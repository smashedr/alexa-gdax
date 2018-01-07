import logging
from django import template

logger = logging.getLogger('app')
register = template.Library()


@register.filter(name='user_display')
def user_display(value):
    return '{}****'.format(str(value)[:4])


@register.filter(name='trim_balance')
def trim_balance(value, length):
    l = value.split('.')
    return '{}.{}'.format(l[0], l[1][:int(length)])
