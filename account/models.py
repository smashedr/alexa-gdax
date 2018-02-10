from __future__ import unicode_literals
import pytz
from django.utils import timezone

from django.db import models


class AccountHistory(models.Model):
    key = models.CharField('API Key', max_length=255, primary_key=True)
    p_day = models.FloatField('Previous Day')
    c_day = models.FloatField('Current Day')
    generated = models.DateTimeField('Date Generated', default=timezone.now)
