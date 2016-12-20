from django.conf.urls import url
from django.views.generic import TemplateView
from apps.connection.views import CreateConnectionView, ListConnectionView, ListConnectorView, TestConnectionView, \
    AJAXFacebookGetAvailableConnectionsView, AJAXFacebookGetAvailableFormsView, AJAXFacebookGetAvailableLeadsView, \
    AJAXMySQLTestConnection, UpdateConnectionView, AJAXSugarCRMTestConnection, AJAXMailChimpTestConnection, \
    GoogleAuthView, AjaxGoogleSpreadSheetTestConnection, GoogleAuthSuccessConnection

urlpatterns = [
    url(r'create/(?P<connector_id>\d+)/$', CreateConnectionView.as_view(), name='create'),
    url(r'update/(?P<connector_id>\d+)/(?P<pk>\d+)/$', UpdateConnectionView.as_view(), name='update'),
    # url(r'delete/(?P<pk>\d+)/$', DeleteGearView.as_view(), name='delete'),
    url(r'list/$', ListConnectionView.as_view(), name='list'),
    url(r'list/connector/$', ListConnectorView.as_view(), name='list_connector'),
    url(r'test/$', TestConnectionView.as_view(), name='test_facebook'),
    url(r"^google_auth/$", GoogleAuthView.as_view(), name="google_auth"),
    url(r"^google_auth/success/$", GoogleAuthSuccessConnection.as_view(), name="google_auth_success"),

    # AJAX
    url(r'ajax/facebook/get/connections/', AJAXFacebookGetAvailableConnectionsView.as_view(),
        name='ajax_update_facebook_get_connections'),
    url(r'ajax/facebook/get/forms/', AJAXFacebookGetAvailableFormsView.as_view(),
        name='ajax_update_facebook_get_forms'),
    url(r'ajax/facebook/get/leads/', AJAXFacebookGetAvailableLeadsView.as_view(),
        name='ajax_update_facebook_get_leads'),
    url(r'ajax/mysql/test_connection/', AJAXMySQLTestConnection.as_view(),
        name='ajax_update_mysql_test_connection'),
    url(r'ajax/sugarcrm/test_connection/', AJAXSugarCRMTestConnection.as_view(),
        name='ajax_sugarcrm_test_connection'),
    url(r'ajax/mailchimp/test_connection/', AJAXMailChimpTestConnection.as_view(),
        name='ajax_mailchimp_test_connection'),
]
