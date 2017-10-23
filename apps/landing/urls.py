from django.conf.urls import url
from apps.landing.views import IndexView, AboutUsView, ContactUsView, AppsView, CustomSignup, StepsView

urlpatterns = [
    url(r'^$', IndexView.as_view(), name='index'),
    url(r'^accounts/signup/$', CustomSignup.as_view(), name='signup'),
    url(r'^about/$', AboutUsView.as_view(), name='about'),
    url(r'^contact/$', ContactUsView.as_view(), name='contact'),
    url(r'^apps/directory/$', AppsView.as_view(), name='apps_directory'),
    url(r'^steps/$', StepsView.as_view(), name='steps'),
]
