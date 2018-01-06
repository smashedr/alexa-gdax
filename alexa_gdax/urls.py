from django.conf import settings
from django.conf.urls import url, include
from django.contrib import admin
from django.views.generic.base import RedirectView

import home.views as home

urlpatterns = [
    url(r'^$', home.home_view, name='home'),
    url(r'^favicon\.ico$', RedirectView.as_view(
        url=settings.STATIC_URL + 'images/favicon.ico'
    )),
    url(r'^api/', include('api.urls')),
    url(r'^oauth/', include('oauth.urls')),
    url(r'^admin/', admin.site.urls, name="django_admin"),
]
