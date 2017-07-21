from django.conf.urls import url
from apps.home.views import HomeView, DashBoardView, IncomingWebhook

urlpatterns = [
    url(r'^$', HomeView.as_view(), name='homepage'),
    url(r'^dashboard/$', DashBoardView.as_view(), name='dashboard'),
    url(r'^webhook/(?P<connector>(\S+))/(?P<webhook_id>(\S+))/$', IncomingWebhook.as_view(), name='webhook'),

]
