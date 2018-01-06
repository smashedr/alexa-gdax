import gdax
import json
import logging
import os
import requests
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from api.alexa import alexa_resp
from api.models import TokenDatabase

logger = logging.getLogger('app')
config = settings.CONFIG['app']

TXT_UNKNOWN = 'I did not understand that request, please try something else.'
TXT_ERROR = 'Error looking up {}, please try something else.'

CURRENCIES = {
    'bitcoin': 'BTC',
    'bitcoin cash': 'BCH',
    'litecoin': 'LTC',
    'ethereum': 'ETH',
}

PRODUCTS = {
    'bitcoin': 'BTC-USD',
    'bitcoin cash': 'BCH-USD',
    'litecoin': 'LTC-USD',
    'ethereum': 'ETH-USD',
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
    # View  /api/alexa
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
        else:
            raise ValueError('Unknown Intent')
    except Exception as error:
        logger.exception(error)
        return alexa_resp('Error. {}'.format(error), 'Error')


def coin_status(event):
    try:
        value = event['request']['intent']['slots']['currency']['value']
        value = value.lower().replace('define', '').strip()
        value = value.lower().replace('lookup', '').strip()
        value = value.lower().replace('look up', '').strip()
        value = value.lower().replace('search', '').strip()
        value = value.lower().replace('find', '').strip()
        logger.info('value: {}'.format(value))
        if value in PRODUCTS:
            url = 'https://api.gdax.com/products/{}/stats'.format(
                PRODUCTS[value]
            )
            r = requests.get(url)
            d = json.loads(r.content.decode())
            speech = ('{} stats for the last 24 hours. '
                      'The low was {}, the high was {} '
                      'and the last price is {}').format(
                PRODUCTS[value][:3],
                round_usd(d['low']),
                round_usd(d['high']),
                round_usd(d['last']),
            )
            return alexa_resp(speech, 'Coin Status')
        else:
            msg = 'Unknown currency {}. Please try one of: {}'.format(
                value, ', '.join([*PRODUCTS])
            )
            return alexa_resp(msg, 'Error')

    except Exception as error:
        logger.info('error: {}'.format(error))
        return alexa_resp(TXT_UNKNOWN, 'Error')


def acct_overview(event):
    try:
        d = get_accounts(event['session']['user']['accessToken'])

        accts = []
        for a in d:
            if int(a['balance'].replace('.', '')) > 0:
                c = {
                    'balance': a['balance'],
                    'currency': a['currency'],
                    'available': a['available'],
                    'hold': a['hold'],
                }
                accts.append(c)

        if not accts:
            msg = 'No accounts with currency found.'
            ar = alexa_resp(msg, 'Accounts Overview')
            logger.info(ar)
            return ar

        speech = 'Found {} account{} of interest. '.format(
            len(accts), 's' if len(accts) > 1 else ''
        )
        for a in accts:
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

        ar = alexa_resp(speech, 'Accounts Overview')
        logger.info(ar)
        return ar
    except Exception as error:
        logger.exception(error)
        return alexa_resp('Error: {}'.format(error), 'Error')


def get_accounts(key):
    try:
        td = TokenDatabase.objects.get(key=key)
        secret = td.secret
        password = td.password

        auth_client = gdax.AuthenticatedClient(key, secret, password)
        gdax_accounts = auth_client.get_accounts()
        logger.info(gdax_accounts)

        return gdax_accounts
    except Exception as error:
        logger.exception(error)
        return False


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
