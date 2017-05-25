from django.conf.urls import url
from apps.wizard.views import CreateGearView, CreatePlugView, CreateConnectionView, TestPlugView, \
    ActionSpecificationsView, CreateGearMapView, ListConnectorView, ListConnectionView, ActionListView, MSSQLFieldList, \
    ListGearView, GoogleDriveSheetList, GoogleSheetsWorksheetList, SugarCRMModuleList, MySQLFieldList, UpdateGearView, \
    PostgreSQLFieldList, FacebookPageList, FacebookFormList, MailChimpListsList, SlackChannelList, SlackWebhookEvent, \
    BitbucketProjectList, BitbucketWebhookEvent, JiraWebhookEvent, JiraProjectList, GetResponseCampaignsList, \
    AJAXGetSurveyListView, InstagramWebhookEvent, InstagramAccountsList

urlpatterns = [
    url(r'^gear/create/$', CreateGearView.as_view(), name='gear_create'),
    url(r'^gear/update/(?P<pk>\d+)/$', UpdateGearView.as_view(), name='gear_update'),
    url(r'^gear/list/$', ListGearView.as_view(), name='gear_list'),
    url(r'gear/map/(?P<gear_id>\d+)/$', CreateGearMapView.as_view(), name='create_gear_map'),
    url(r'^connector/list/(?P<type>(source|target)+)/$', ListConnectorView.as_view(), name='connector_list'),
    url(r'connection/create/(?P<connector_id>\d+)/$', CreateConnectionView.as_view(), name='create_connection'),
    url(r'^connection/list/(?P<connector_id>\d+)/(?P<type>(source|target)+)/$', ListConnectionView.as_view(),
        name='connection_list'),
    url(r'^plug/create/(?P<plug_type>(source|target)+)/$', CreatePlugView.as_view(), name='plug_create'),
    url('^plug/test/(?P<pk>\d+)/$', TestPlugView.as_view(), name='plug_test'),
    url(r'^plug/action/list/$', ActionListView.as_view(), name='action_list'),
    url(r'^plug/action/(?P<pk>\d+)/specifications/$', ActionSpecificationsView.as_view(), name='action_specifications'),
    # PLUG CREATION ASYNC

    # GoogleSheets
    url(r"async/google/drive/sheets/list/", GoogleDriveSheetList.as_view(), name='async_google_drive_sheets'),
    url(r"async/google/sheet/worksheets/", GoogleSheetsWorksheetList.as_view(), name='async_google_sheet_worksheets'),
    # SugarCRM
    url(r"async/sugarcrm/module/list/", SugarCRMModuleList.as_view(), name='async_sugarcrm_modules'),
    # MySQL
    url(r"async/mysql/field/list/", MySQLFieldList.as_view(), name='async_mysql_fields'),
    url(r"async/mssql/field/list/", MSSQLFieldList.as_view(), name='async_mssql_fields'),
    # PostgreSQL
    url(r"async/postgresql/field/list/", PostgreSQLFieldList.as_view(), name='async_postgresql_fields'),
    # Facebook
    url(r"async/facebook/page/list/", FacebookPageList.as_view(), name='async_facebook_pages'),
    url(r"async/facebook/form/list/", FacebookFormList.as_view(), name='async_facebook_forms'),
    # MailChimp
    url(r'async/mailchimp/lists/list/', MailChimpListsList.as_view(), name='async_mailchimp_lists'),

    # Slack
    url(r'async/slack/channel/list/', SlackChannelList.as_view(), name='async_slack_chanels'),
    url(r'slack/webhook/event/', SlackWebhookEvent.as_view(), name='slack_webhook_event'),
    # Bitbucket
    url(r'async/bitbucket/field/list/', BitbucketProjectList.as_view(), name='async_bitbucket_projects'),
    url(r'bitbucket/webhook/event/', BitbucketWebhookEvent.as_view(), name='bitbucket_webhook_event'),
    # Jira
    url(r"async/jira/field/list/", JiraProjectList.as_view(), name='async_jira_projects'),
    url(r'jira/webhook/event/', JiraWebhookEvent.as_view(), name='jira_webhook_event'),
    # GetResponse
    url(r"async/getresponse/campaigns/list/", GetResponseCampaignsList.as_view(), name='async_getresponse_campaigns'),

    # SurveyMonkey
    url("async/surveymonkey/survey/list/", AJAXGetSurveyListView.as_view(), name='async_surveymonkey_survey_list'),

    # Instagram
    url(r'instagram/webhook/event/', InstagramWebhookEvent.as_view(), name='instagram_webhook_event'),
    url("async/instagram/accounts/list/", InstagramAccountsList.as_view(), name='async_instagram_accounts'),
]
