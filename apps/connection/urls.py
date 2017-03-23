from django.conf.urls import url
from django.views.generic import TemplateView
from apps.connection.views import CreateConnectionView, ListConnectionView, ListConnectorView, \
    AJAXFacebookGetAvailableConnectionsView, AJAXFacebookGetAvailableFormsView, AJAXFacebookGetAvailableLeadsView, \
    AJAXMySQLTestConnection, UpdateConnectionView, AJAXSugarCRMTestConnection, AJAXMailChimpTestConnection, \
    GoogleAuthView, AjaxGoogleSpreadSheetTestConnection, GoogleAuthSuccessCreateConnection, \
    AJAXPostgreSQLTestConnection, AJAXMSSQLTestConnection, AJAXBitbucketTestConnection

urlpatterns = [
    url(r'create/(?P<connector_id>\d+)/$', CreateConnectionView.as_view(), name='create'),
    url(r'update/(?P<connector_id>\d+)/(?P<pk>\d+)/$', UpdateConnectionView.as_view(), name='update'),
    # url(r'delete/(?P<pk>\d+)/$', DeleteGearView.as_view(), name='delete'),
    url(r'list/$', ListConnectionView.as_view(), name='list'),
    url(r'list/connector/$', ListConnectorView.as_view(), name='list_connector'),
    url(r"^google_auth/$", GoogleAuthView.as_view(), name="google_auth"),
    url(r"^google_auth/success/$", GoogleAuthSuccessCreateConnection.as_view(),
        name="google_auth_success_create_connection"),

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
    url(r'ajax/postgresql/test_connection/', AJAXPostgreSQLTestConnection.as_view(),
        name='ajax_update_postgresql_test_connection'),
    url(r'ajax/mssql/test_connection/', AJAXMSSQLTestConnection.as_view(),
        name='ajax_update_mssql_test_connection'),
    url(r'ajax/bitbucket/test_connection/', AJAXBitbucketTestConnection.as_view(),
        name='ajax_update_bitbucket_test_connection'),
]
