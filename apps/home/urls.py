from django.conf.urls import url
from apps.home.views import DashBoardView, IncomingWebhook, HelpView, TermsView, \
    SubscriptionsManagerView

urlpatterns = [
    url(r'^dashboard/$', DashBoardView.as_view(), name='dashboard'),
    url(r'^webhook/(?P<connector>(\S+))/(?P<webhook_id>(\S+))/$', IncomingWebhook.as_view(), name='webhook'),
    url(r'^help/$', HelpView.as_view(), name='help'),

    url(r'^terms/$', TermsView.as_view(), name='terms'),
    url(r'^subscriptions/$', SubscriptionsManagerView.as_view(), name='subscriptions_manager'),

]
