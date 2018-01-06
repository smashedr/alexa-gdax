from django.conf.urls import url

import api.views as api

urlpatterns = [
    url(r'^$', api.api_home, name='api_home'),
    url(r'alexa/', api.alexa_post, name='alexa'),
]
