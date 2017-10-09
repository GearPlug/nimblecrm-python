from django.conf.urls import url
from apps.landing.views import IndexView, AboutUsView

urlpatterns = [
    url(r'^$', IndexView.as_view(), name='indexpage'),
    url(r'^aboutus/$', AboutUsView.as_view(), name='aboutus'),
]
