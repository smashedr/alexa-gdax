import logging
from account.models import AccountHistory
from django.core.management.base import BaseCommand
from account.views import get_accounts, get_total_account_value

logger = logging.getLogger('app')


class Command(BaseCommand):
    help = 'Rotate Stats Nightly.'

    def handle(self, **options):
        for acct in AccountHistory.objects.all():
            logger.info('Rotating Account History: {}'.format(acct.key[:5]))
            gdax_accounts = get_accounts(acct.key)
            value = get_total_account_value(gdax_accounts)
            h = AccountHistory.objects.get(key=acct.key)

            logger.info('Setting p_day: {} to c_day: {}'.format(
                h.p_day, h.c_day
            ))
            h.p_day = h.c_day

            logger.info('Setting c_day: {} to value: {}'.format(
                h.c_day, value
            ))
            h.c_day = value

            h.save()
