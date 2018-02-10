import gdax
import json
import logging
import re
import requests
import requests_cache
from django.conf import settings
from django.shortcuts import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from api.alexa import alexa_resp
from api.models import TokenDatabase

logger = logging.getLogger('app')
config = settings.CONFIG['app']

requests_cache.install_cache('pub-requests', backend='sqlite', expire_after=15)

PRODUCTS = {
    'BTC': {
        'product': 'BTC-USD',
        'short': 'BTC',
        'name': 'bitcoin',
        're': 'bit',
    },
    'BCH': {
        'product': 'BCH-USD',
        'short': 'BCH',
        'name': 'bitcoin cash',
        're': 'cash',
    },
    'LTC': {
        'product': 'LTC-USD',
        'short': 'LTC',
        'name': 'litecoin',
        're': '(lite|light)',
    },
    'ETH': {
        'product': 'ETH-USD',
        'short': 'ETH',
        'name': 'ethereum',
        're': 'eth',
    },
}


def api_home(request):
    """
    # View  /api/
    """
    log_req(request)
    return HttpResponse('Online')


@csrf_exempt
@require_http_methods(["POST"])
def alexa_post(request):
    """
    View  /api/alexa
    """
    log_req(request)
    try:
        body = request.body.decode('utf-8')
        event = json.loads(body)
        logger.info(event)
        intent = event['request']['intent']['name']
        if intent == 'AccountOverview':
            return acct_overview(event)
        elif intent == 'CoinStatus':
            return coin_status(event)
        elif intent == 'AccountValue':
            return account_value(event)
        elif intent == 'CoinValue':
            return coin_value(event)
        else:
            raise ValueError('Unknown Intent')
    except Exception as error:
        logger.exception(error)
        return alexa_resp('Error. {}'.format(error), 'Error')


def coin_value(event):
    # Alexa Response - CoinValue
    try:
        value = event['request']['intent']['slots']['currency']['value']
        logger.info('value: {}'.format(value))
        product = get_product_info(value)
        accounts = get_accounts(event['session']['user']['accessToken'])
        account = get_account(accounts, product)
        value = get_account_value(account)
        speech = 'Your {} account is currently valued at {} USD.'.format(
            product['short'], value
        )
        return alexa_resp(speech, 'Accounts Overview')
    except Exception as error:
        logger.exception(error)
        return alexa_resp('Error: {}'.format(error), 'Error')


def account_value(event):
    # Alexa Response - AccountValue
    try:
        d = get_accounts(event['session']['user']['accessToken'])
        accounts = get_accounts_of_value(d)
        total_value = get_total_account_value(accounts)
        s = '' if len(accounts) == 1 else 's'
        speech = 'Your total account value over {} account{} is {} USD.'.format(
            len(accounts), s, total_value
        )
        return alexa_resp(speech, 'Accounts Overview')
    except Exception as error:
        logger.exception(error)
        return alexa_resp('Error: {}'.format(error), 'Error')


def coin_status(event):
    # Alexa Response - CoinStatus
    try:
        value = event['request']['intent']['slots']['currency']['value']
        logger.info('value: {}'.format(value))
        product = get_product_info(value)
        if product:
            d = get_gdax_product(product)
            speech = ('{} stats for the last 24 hours. '
                      'The low was {}, the high was {}, '
                      'and the last price is {}').format(
                product['short'],
                round_usd(d['low']),
                round_usd(d['high']),
                round_usd(d['last']),
            )
            return alexa_resp(speech, 'Coin Status')
        else:
            msg = 'Unknown currency {}. Please try one of: {}'.format(
                value, get_product_list()
            )
            return alexa_resp(msg, 'Error')
    except Exception as error:
        logger.info('error: {}'.format(error))
        return alexa_resp('Error. {}'.format(error), 'Error')


def acct_overview(event):
    # Alexa Response - AccountOverview
    try:
        d = get_accounts(event['session']['user']['accessToken'])
        accounts = get_accounts_of_value(d)
        if not accounts:
            msg = 'No accounts with currency found.'
            return alexa_resp(msg, 'Accounts Overview')

        speech = 'Found {} account{} of interest. '.format(
            len(accounts), '' if len(accounts) == 1 else 's'
        )
        for a in accounts:
            if a['currency'] == 'USD':
                balance = '{} dollars'.format(
                    round_usd(a['balance'])
                )
                available = round_usd(a['available'])
                hold = round_usd(a['hold'])
            else:
                balance = a['balance']
                if balance.endswith('0'):
                    balance = '{}0'.format(balance.rstrip('0'))
                available = a['available']
                if available.endswith('0'):
                    available = '{}0'.format(available.rstrip('0'))
                hold = a['hold']
                if hold.endswith('0'):
                    hold = '{}0'.format(hold.rstrip('0'))

            speech += '{} account contains {}. '.format(
                a['currency'], balance
            )
            if no_float(available) > 0 \
                    and round_usd(a['balance']) != round_usd(a['available']):
                speech += '{} is available '.format(available)

            if no_float(hold) > 0:
                speech += 'with {} on hold. '.format(hold)

        return alexa_resp(speech, 'Accounts Overview')
    except Exception as error:
        logger.exception(error)
        return alexa_resp('Error: {}'.format(error), 'Error')


def get_accounts_of_value(accounts):
    accounts_list = []
    for a in accounts:
        if int(a['balance'].replace('.', '')) > 0:
            c = {
                'balance': a['balance'],
                'currency': a['currency'],
                'available': a['available'],
                'hold': a['hold'],
            }
            accounts_list.append(c)
    return accounts_list


def get_accounts(key):
    try:
        with requests_cache.disabled():
            secret, password = get_secrets(key)
            auth_client = gdax.AuthenticatedClient(key, secret, password)
            gdax_accounts = auth_client.get_accounts()
            return gdax_accounts
    except Exception as error:
        logger.exception(error)
        return False


def get_account(accounts, product):
    for a in accounts:
        if 'currency' in a:
            if a['currency'] == product['short']:
                return a
    return None


def get_total_account_value(accounts):
    total = 0
    for a in accounts:
        value = get_account_value(a)
        total += value
    return round_usd(total)


def get_account_value(account):
    if account['currency'] == 'USD':
        return round_usd(account['balance'])
    product = PRODUCTS[account['currency']]
    d = get_gdax_product(product)
    last = d['last']
    balance = account['balance']
    value = float(balance) * float(last)
    return round_usd(value)


def get_gdax_product(product):
    url = 'https://api.gdax.com/products/{}/stats'.format(
        product['product']
    )
    r = requests.get(url)
    return r.json()


def get_secrets(key):
    try:
        td = TokenDatabase.objects.get(key=key)
        secret = td.secret
        password = td.password
        return secret, password
    except Exception as error:
        logger.exception(error)
        return None, None


def get_product_info(slot):
    logger.info('slot: {}'.format(slot))
    if re.search(PRODUCTS['BTC']['re'], slot):
        return PRODUCTS['BTC']
    if re.search(PRODUCTS['BCH']['re'], slot):
        return PRODUCTS['BCH']
    if re.search(PRODUCTS['LTC']['re'], slot):
        return PRODUCTS['LTC']
    if re.search(PRODUCTS['ETH']['re'], slot):
        return PRODUCTS['ETH']
    return False


def get_product_list():
    l = []
    for k, v in PRODUCTS.items():
        l.append(v['name'])
    return ', '.join(l)


def round_usd(in_float):
    return round(float(in_float), 2)


def no_float(in_float):
    return int(str(in_float).replace('.', ''))


def log_req(request):
    """
    DEBUGGING ONLY
    """
    data = ''
    if request.method == 'GET':
        logger.debug('GET')
        for key, value in request.GET.items():
            data += '"%s": "%s", ' % (key, value)
    if request.method == 'POST':
        logger.debug('POST')
        for key, value in request.POST.items():
            data += '"%s": "%s", ' % (key, value)
    data = data.strip(', ')
    logger.debug(data)
    json_string = '{%s}' % data
    return json_string
