import logging
from django import template

logger = logging.getLogger('app')
register = template.Library()


@register.filter(name='user_display')
def user_display(value):
    return '{}****'.format(str(value)[:4])
