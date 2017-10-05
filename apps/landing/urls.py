from django.conf.urls import url
from apps.landing.views import IndexView
urlpatterns = [
    url(r'^$', IndexView.as_view(), name='indexpage'),
]