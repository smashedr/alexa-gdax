from django.conf.urls import url

import oauth.views as oauth

urlpatterns = [
    url(r'authorize/', oauth.do_authorize, name='authorize'),
    url(r'verify/', oauth.do_verify, name='verify'),
    url(r'token/', oauth.give_token, name='token'),
    url(r'error/', oauth.has_error, name='error'),
]
