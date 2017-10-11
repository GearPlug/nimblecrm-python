from django.conf.urls import url
from apps.landing.views import IndexView, AboutUsView, ContactUsView, AppsView

urlpatterns = [
    url(r'^$', IndexView.as_view(), name='index'),
    url(r'^about/$', AboutUsView.as_view(), name='about'),
    url(r'^contact/$', ContactUsView.as_view(), name='contact'),
    url(r'^apps/directory/$', AppsView.as_view(), name='apps_directory'),
]
