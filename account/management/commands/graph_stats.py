import logging
import statsd
from account.models import AccountHistory
from django.core.management.base import BaseCommand
from django.conf import settings
from api.views import get_accounts, get_total_account_value

config = settings.CONFIG['app']
logger = logging.getLogger('app')


def add_stat(prefix, value):
    """
    Add a Metric
    """
    print(config)
    stats = statsd.StatsClient(config['stats_host'], int(config['stats_port']))
    metric = '{}.{}'.format(
        config['stats_prefix'],
        prefix,
    )
    print(metric)
    print(value)
    stats.gauge(metric, value)


class Command(BaseCommand):
    help = 'Graph Total Stats.'

    def handle(self, **options):
        for acct in AccountHistory.objects.all():
            gdax_accounts = get_accounts(str(acct.key))
            value = get_total_account_value(gdax_accounts)
            add_stat(acct.key[:5], int(value))
