from django.conf.urls import url
from apps.connection.views import CreateConnectionView, ListConnectorView, \
    AJAXFacebookGetAvailableConnectionsView, AJAXFacebookGetAvailableFormsView, AJAXFacebookGetAvailableLeadsView, \
    AJAXMySQLTestConnection, UpdateConnectionView, AJAXSugarCRMTestConnection, AJAXMailChimpTestConnection, \
    GoogleAuthView, AjaxGoogleSpreadSheetTestConnection, GoogleAuthSuccessCreateConnection, \
    AJAXPostgreSQLTestConnection, AJAXMSSQLTestConnection, SlackAuthView, AuthSuccess, AJAXBitbucketTestConnection, \
    AJAXJiraTestConnection, AJAXGetResponseTestConnection, TwitterAuthView, TwitterAuthSuccessCreateConnection, \
    SurveyMonkeyAuthView, SurveyMonkeyAuthSuccessCreateConnection, InstagramAuthView, \
    SurveyMonkeyAuthSuccessCreateConnection, AJAXGetSurveyListView, InstagramAuthSuccessCreateConnection, \
    AJAXZohoCRMTestConnection, AJAXSMSTestConnection, AJAXSalesforceTestConnection, SalesforceAuthView, \
    SalesforceAuthSuccessCreateConnection
from apps.gp.enum import GoogleAPI

urlpatterns = [
    # CRUD?
    url(r'create/(?P<connector_id>\d+)/$', CreateConnectionView.as_view(), name='create'),
    url(r'update/(?P<connector_id>\d+)/(?P<pk>\d+)/$', UpdateConnectionView.as_view(), name='update'),
    # url(r'delete/(?P<pk>\d+)/$', DeleteGearView.as_view(), name='delete'),
    url(r'list/connector/$', ListConnectorView.as_view(), name='list_connector'),

    # Google SpreadSheets
    url(r"^google_auth/$", GoogleAuthView.as_view(), {'api': GoogleAPI.SpreadSheets}, name="google_auth"),
    url(r"^google_auth/success/$", GoogleAuthSuccessCreateConnection.as_view(), {'api': GoogleAPI.SpreadSheets},
        name="google_auth_success_create_connection"),

    # Google Forms
    url(r"^google_forms_auth/$", GoogleAuthView.as_view(), {'api': GoogleAPI.Forms}, name="google_forms_auth"),
    url(r"^google_forms_auth/success/$", GoogleAuthSuccessCreateConnection.as_view(), {'api': GoogleAPI.Forms},
        name="google_forms_auth_success_create_connection"),

    # Google Calendar
    url(r"^google_calendar_auth/$", GoogleAuthView.as_view(), {'api': GoogleAPI.Calendar}, name="google_calendar_auth"),
    url(r"^google_calendar_auth/success/$", GoogleAuthSuccessCreateConnection.as_view(), {'api': GoogleAPI.Calendar},
        name="google_calendar_auth_success_create_connection"),

    # Google YouTube
    url(r"^google_youtube_auth/$", GoogleAuthView.as_view(), {'api': GoogleAPI.YouTube}, name="google_youtube_auth"),
    url(r"^google_youtube_auth/success/$", GoogleAuthSuccessCreateConnection.as_view(), {'api': GoogleAPI.YouTube},
        name="google_youtube_auth_success_create_connection"),

    # Twitter
    url(r"^twitter_auth/$", TwitterAuthView.as_view(), name="twitter_auth"),
    url(r"^twitter_auth/success/$", TwitterAuthSuccessCreateConnection.as_view(),
        name="twitter_auth_success_create_connection"),

    # Instagram
    url(r"^instagram_auth/$", InstagramAuthView.as_view(), name="instagram_auth"),
    url(r"^instagram_auth/success/$", InstagramAuthSuccessCreateConnection.as_view(),
        name="instagram_auth_success_create_connection"),

    # SalesForce
    url(r"^salesforce_auth/$", SalesforceAuthView.as_view(), name="salesforce_auth"),
    url(r"^salesforce_auth/success/$", SalesforceAuthSuccessCreateConnection.as_view(),
        name="salesforce_auth_success_create_connection"),

    # surveymonkey
    url(r"^survey_monkey_auth/$", SurveyMonkeyAuthView.as_view(), name="survey_monekey_auth"),
    url(r"^survey_monkey_auth/success/$", SurveyMonkeyAuthSuccessCreateConnection.as_view(),
        name="survey_monkey_auth_success_create_connection"),
    # Slack
    url(r'^auth/slack/', SlackAuthView.as_view(), name="slack_auth"),

    # AuthSuccess
    url(r'^auth/success/$', AuthSuccess.as_view(), name="auth_sucess"),

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
    url(r'ajax/jira/test_connection/', AJAXJiraTestConnection.as_view(),
        name='ajax_update_jira_test_connection'),
    url(r'ajax/getresponse/test_connection/', AJAXGetResponseTestConnection.as_view(),
        name='ajax_update_getresponse_test_connection'),
    url(r'ajax/zohocrm/test_connection/', AJAXZohoCRMTestConnection.as_view(),
        name='ajax_zohocrm_test_connection'),
    url(r'ajax/sms/test_connection/', AJAXSMSTestConnection.as_view(),
        name='ajax_update_sms_test_connection'),
    url(r'ajax/salesforce/test_connection/', AJAXSalesforceTestConnection.as_view(),
        name='ajax_update_salesforce_test_connection'),

]
