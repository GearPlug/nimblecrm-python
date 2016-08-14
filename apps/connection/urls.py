from django.conf.urls import url
from apps.connection.views import CreateConnectionView, UpdateConnectionView, DeleteConnectionView, ListConnectionView, \
    ListConnectorView

urlpatterns = [
    url(r'create/(?P<connector_id>\d+)/$', CreateConnectionView.as_view(), name='create'),
    # url(r'update/(?P<pk>\d+)/$', UpdateGearView.as_view(), name='update'),
    # url(r'delete/(?P<pk>\d+)/$', DeleteGearView.as_view(), name='delete'),
    url(r'list/$', ListConnectionView.as_view(), name='list'),
    url(r'list/connector/$', ListConnectorView.as_view(), name='list_connector'),
]
