from django.conf.urls import url
from apps.landing.views import IndexView, AboutUsView, ContactUsView, AppsView

urlpatterns = [
    url(r'^$', IndexView.as_view(), name='indexpage'),
    url(r'^aboutus/$', AboutUsView.as_view(), name='aboutus'),
    url(r'^contactus/$', ContactUsView.as_view(), name='contactus'),
    url(r'^apps/$', AppsView.as_view(), name='apps'),
]
