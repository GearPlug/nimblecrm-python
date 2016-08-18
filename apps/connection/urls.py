from django.conf.urls import url
from apps.connection.views import CreateConnectionView, ListConnectionView, ListConnectorView, TestConnectionView, \
    AJAXSetUserFacebookToken, AJAXFacebookGetAvailableConnectionsView, AJAXFacebookGetAvailableFormsView, \
    AJAXFacebookGetAvailableLeadsView, AJAXMySQLTestConnection, UpdateConnectionView

urlpatterns = [
    url(r'create/(?P<connector_id>\d+)/$', CreateConnectionView.as_view(), name='create'),
    url(r'update/(?P<connector_id>\d+)/(?P<pk>\d+)/$', UpdateConnectionView.as_view(), name='update'),
    # url(r'delete/(?P<pk>\d+)/$', DeleteGearView.as_view(), name='delete'),
    url(r'list/$', ListConnectionView.as_view(), name='list'),
    url(r'list/connector/$', ListConnectorView.as_view(), name='list_connector'),
    url(r'test/$', TestConnectionView.as_view(), name='test_facebook'),

    # AJAX
    url(r'ajax/update/facebook/token/(?P<pk>\d+)/$', AJAXSetUserFacebookToken.as_view(),
        name='ajax_update_facebook_token'),
    url(r'ajax/update/facebook/get/connections/', AJAXFacebookGetAvailableConnectionsView.as_view(),
        name='ajax_update_facebook_get_connections'),
    url(r'ajax/update/facebook/get/forms/', AJAXFacebookGetAvailableFormsView.as_view(),
        name='ajax_update_facebook_get_forms'),
    url(r'ajax/update/facebook/get/leads/', AJAXFacebookGetAvailableLeadsView.as_view(),
        name='ajax_update_facebook_get_leads'),
    url(r'ajax/update/mysql/test_connection/', AJAXMySQLTestConnection.as_view(),
        name='ajax_update_mysql_test_connection'),
]
