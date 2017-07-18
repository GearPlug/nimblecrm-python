from django.conf.urls import url
from apps.wizard.views import MSSQLFieldList, GoogleDriveSheetList, GoogleSheetsWorksheetList, SugarCRMModuleList, \
    MySQLFieldList, PostgreSQLFieldList, FacebookPageList, FacebookFormList, MailChimpListsList, SlackChannelList, \
    SlackWebhookEvent, BitbucketProjectList, BitbucketWebhookEvent, JiraWebhookEvent, JiraProjectList, \
    GetResponseCampaignsList, InstagramWebhookEvent, InstagramAccountsList, PaypalWebhookEvent, GoogleCalendarsList, \
    GoogleCalendarWebhookEvent, AJAXGetSurveyListView, SurveyMonkeyWebhookEvent, ZohoCRMModuleList, YouTubeWebhookEvent, \
    YouTubeChannelsList, ShopifyList, ShopifyWebhookEvent

from apps.connection.views import ListConnectionView, ListConnectorView, CreateConnectionView
from apps.gear.views import ListGearView, CreateGearView, UpdateGearView, DeleteGearView, CreateGearMapView
from apps.plug.views import ActionListView, ActionSpecificationsListView, CreatePlugView, TestPlugView

urlpatterns = [

    # WIZARD EN ORDEN

    # GEAR LIST
    url(r'^gear/list/$', ListGearView.as_view(), name='gear_list'),
    # GEAR CREATE OR UPDATE
    url(r'^gear/create/$', CreateGearView.as_view(), name='gear_create'),
    url(r'^gear/update/(?P<pk>\d+)/$', UpdateGearView.as_view(), name='gear_update'),
    # CONNECTOR LIST
    url(r'^connector/list/(?P<type>(source|target)+)/$', ListConnectorView.as_view(), name='connector_list'),
    # CONNECTION LIST
    url(r'^connection/list/(?P<connector_id>\d+)/(?P<type>(source|target)+)/$', ListConnectionView.as_view(),
        name='connection_list'),
    # CONNECTION CREATE
    url(r'^connection/create/(?P<connector_id>\d+)/$', CreateConnectionView.as_view(), name='create_connection'),
    # PLUG CREATE
    url(r'^plug/create/(?P<plug_type>(source|target)+)/$', CreatePlugView.as_view(), name='plug_create'),
    # PLUG ACTION LIST (AJAX)
    url(r'^plug/action/(?P<pk>\d+)/specifications/$', ActionSpecificationsListView.as_view(),
        name='action_specifications'),
    # PLUG ACTION SPECIFICATION LIST (AJAX)
    url(r'^plug/action/list/$', ActionListView.as_view(), name='action_list'),
    # PLUG TEST
    url('^plug/test/(?P<pk>\d+)/$', TestPlugView.as_view(), name='plug_test'),
    # GEAR MAP
    url(r'^gear/map/(?P<gear_id>\d+)/$', CreateGearMapView.as_view(), name='create_gear_map'),

    # PLUG CREATION SPECIFICS FOR CONNECTOR
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
    url(r"async/surveymonkey/survey/list/", AJAXGetSurveyListView.as_view(), name='async_surveymonkey_survey_list'),
    url(r'surveymonkey/webhook/event/(?P<plug_id>\d+)/', SurveyMonkeyWebhookEvent.as_view(),
        name='surveymonkey_webhook_event'),

    # Shopify
    url(r"async/shopify/topic/list/", ShopifyList.as_view(), name='async_shopify_topic_list'),
    url(r'shopify/webhook/event/(?P<plug_id>\d+)/', ShopifyWebhookEvent.as_view(),
        name='shopify_webhook_event'),

    # Instagram
    url(r'instagram/webhook/event/', InstagramWebhookEvent.as_view(), name='instagram_webhook_event'),
    url("async/instagram/accounts/list/", InstagramAccountsList.as_view(), name='async_instagram_accounts'),

    # Paypal
    url(r'paypal/webhook/event/', PaypalWebhookEvent.as_view(), name='paypal_webhook_event'),
    # GoogleCalendar
    url(r"async/google/calendars/list/", GoogleCalendarsList.as_view(), name='async_google_calendars'),
    url(r'google/calendar/webhook/event/', GoogleCalendarWebhookEvent.as_view(), name='googlecalendar_webhook_event'),

    # YouTube
    url(r"async/youtube/channels/list/", YouTubeChannelsList.as_view(), name='async_youtube_channels'),
    url(r'youtube/webhook/event/', YouTubeWebhookEvent.as_view(), name='youtube_webhook_event'),

    # ZohoCRM
    url(r"async/zohocrm/module/list/", ZohoCRMModuleList.as_view(), name='async_zohorcrm_modules'),

]
