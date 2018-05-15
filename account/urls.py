from django.conf.urls import url

import account.views as account

urlpatterns = [
    url(r'^$', account.account_home, name='account_home'),
    url(r'balance/', account.show_balance, name='show_balance'),
    url(r'update/', account.update_balance, name='update_balance'),
    url(r'holdings/(?P<userid>[a-zA-Z0-9]{5})/(?P<ticker>[a-zA-Z]{1,5})',
        account.get_holding, name='get_holding'),
    url(r'login/', account.show_login, name='login'),
    url(r'auth/', account.do_login, name='auth'),
    url(r'logout/', account.do_logout, name='logout'),
]
