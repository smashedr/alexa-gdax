import logging
import re
from django.contrib.auth import login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render, redirect, HttpResponseRedirect
from django.views.decorators.http import require_http_methods
from api.models import TokenDatabase
from account.models import AccountHistory
from api.views import get_accounts, get_account_value, get_total_account_value

logger = logging.getLogger('app')


@login_required
@require_http_methods(["GET"])
def account_home(request):
    """
    View  /account/
    """
    gdax_accounts = get_accounts(str(request.user))
    accounts = []
    for a in gdax_accounts:
        value = get_account_value(a)
        account = {
            'currency': a['currency'],
            'balance': a['balance'],
            'value': value,
        }
        accounts.append(account)

    value = get_total_account_value(gdax_accounts)
    account_values = cal_history(request.user.username, value)
    return render(request, 'account/home.html', {
        'accounts': accounts,
        'balance': account_values,
    })


@require_http_methods(['GET'])
def show_balance(request):
    """
    View  /account/balance/
    """
    log_req(request)
    return render(request, 'account/balance.html')


@require_http_methods(['POST'])
def update_balance(request):
    """
    View  /account/update/
    """
    log_req(request)
    try:
        _amount = request.POST.get('amount')
        _action = request.POST.get('action')
        logger.info('_amount: {}'.format(_amount))
        logger.info('_action: {}'.format(_action))
        m = re.search('\d+(\.\d{1,2})?', _amount)
        logger.info(m)
        if m:
            amount = round(float(m.group(0)), 2)
            logger.info('amount: {}'.format(amount))
            h = AccountHistory.objects.get(key=request.user.username)
            if _action == 'increase':
                txt = 'Increased'
                process_update(request, _action, amount)
            elif _action == 'decrease':
                txt = 'Decreased'
                process_update(request, _action, amount)
            else:
                raise ValueError('Unknown Action. Try Again.')
            return msg_redirect(
                request, messages.SUCCESS, 'success',  'account_home',
                'Balance successfully {} by {}'.format(txt, amount),
            )
        else:
            raise ValueError('Invalid Input for Balance.')
    except Exception as error:
        logger.exception(error)
        return msg_redirect(
            request, messages.WARNING, 'danger',  'show_balance',
            'Error Updating Balance:<br>{}'.format(error),
        )


@require_http_methods(['GET'])
def show_login(request):
    """
    View  /account/logout/
    """
    log_req(request)
    request.session['login_next_url'] = get_next_url(request)
    return render(request, 'account/login.html')


@require_http_methods(['POST'])
def do_logout(request):
    """
    View  /account/logout/
    """
    log_req(request)
    next_url = get_next_url(request)
    logout(request)
    request.session['login_next_url'] = next_url
    return redirect(next_url)


@require_http_methods(['POST'])
def do_login(request):
    """
    View  /account/login/
    """
    log_req(request)
    try:
        _key = request.POST.get('key')
        _password = request.POST.get('password')
        td = TokenDatabase.objects.get(key=_key)
        if _password == td.password:
            if login_user(request, _key):
                return HttpResponseRedirect(get_next_url(request))
            else:
                raise ValueError('Logging in user failed.')
        else:
            return msg_redirect(
                request, messages.SUCCESS, 'danger',  'login',
                'Incorrect Password. Please Try Again.',
            )
    except Exception as error:
        logger.exception(error)
        return msg_redirect(
            request, messages.WARNING, 'danger',  'login',
            'Invalid Key. Please Try Again.',
        )


def process_update(request, action, amount):
    h = AccountHistory.objects.get(key=request.user.username)
    if action == 'increase':
        h.c_day = h.c_day + amount
        h.p_day = h.p_day + amount
        h.save()
    elif action == 'decrease':
        h.c_day = h.c_day - amount
        h.p_day = h.p_day - amount
        h.save()
    else:
        raise ValueError('Unknown Action. Try Again.')


def cal_history(username, value):
    try:
        h = AccountHistory.objects.get(key=username)
    except ObjectDoesNotExist:
        logger.info('Creating AccountHistory Object.')
        h = AccountHistory(
            key=username,
            p_day=float(value),
            c_day=float(value),
        )
        h.save()
    except Exception as error:
        logger.exception(error)
        raise error

    c_tot = round(value - h.c_day, 2)
    if c_tot > 0:
        c_per = round(c_tot/h.c_day*100, 2)
        c_pos = True
    elif c_tot < 0:
        c_per = round(-c_tot/h.c_day*100, 2)
        c_pos = False
    else:
        c_per = 0
        c_pos = True

    p_tot = round(value - h.p_day, 2)
    if p_tot > 0:
        p_per = round(p_tot/h.p_day*100, 2)
        p_pos = True
    elif p_tot < 0:
        p_per = round(-p_tot/h.p_day*100, 2)
        p_pos = False
    else:
        p_per = 0
        p_pos = True

    account_values = {
        'value': value,
        'c_tot': c_tot,
        'c_per': c_per,
        'c_pos': c_pos,
        'p_tot': p_tot,
        'p_per': p_per,
        'p_pos': p_pos,
    }

    return account_values


def login_user(request, username):
    """
    Login or Create New User
    """
    try:
        user = User.objects.filter(username=username).get()
        login(request, user)
        return True
    except ObjectDoesNotExist:
        user = User.objects.create_user(username)
        user.save()
        login(request, user)
        return True
    except Exception as error:
        logger.exception(error)
        return False


def get_next_url(request):
    """
    Determine 'next' Parameter
    """
    try:
        next_url = request.GET['next']
    except:
        try:
            next_url = request.POST['next']
        except:
            try:
                next_url = request.session['login_next_url']
            except:
                next_url = '/'
    if not next_url:
        next_url = '/'
    if '?next=' in next_url:
        next_url = next_url.split('?next=')[1]
    return next_url


def msg_redirect(request, msg_type, tags, location, message):
    messages.add_message(request, msg_type, message, extra_tags=tags)
    return redirect(location)


def log_req(request):
    """
    DEBUGGING ONLY
    """
    data = ''
    if request.method == 'GET':
        data = 'GET: '
        for key, value in request.GET.items():
            data += '"%s": "%s", ' % (key, value)
    if request.method == 'POST':
        data = 'POST: '
        for key, value in request.POST.items():
            data += '"%s": "%s", ' % (key, value)
    if data:
        data = data.strip(', ')
        logger.info(data)
        json_string = '{%s}' % data
        return json_string
    else:
        return None
