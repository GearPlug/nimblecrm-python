from django.conf.urls import url

from apps.wizard.views import JiraWebhookEvent, JiraProjectList, \
     PaypalWebhookEvent, \
     ZohoCRMModuleList, YouTubeWebhookEvent, \
    YouTubeChannelsList, ShopifyList, ShopifyWebhookEvent, SalesforceSObjectList, SalesforceEventList, \
    SalesforceWebhookEvent

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
    # Jira
    url(r"async/jira/field/list/", JiraProjectList.as_view(), name='async_jira_projects'),
    url(r'jira/webhook/event/', JiraWebhookEvent.as_view(), name='jira_webhook_event'),
    # GetResponse

    # Shopify
    url(r"async/shopify/topic/list/", ShopifyList.as_view(), name='async_shopify_topic_list'),
    url(r'shopify/webhook/event/(?P<plug_id>\d+)/', ShopifyWebhookEvent.as_view(),
        name='shopify_webhook_event'),

    # Paypal
    url(r'paypal/webhook/event/', PaypalWebhookEvent.as_view(), name='paypal_webhook_event'),

    # YouTube
    url(r"async/youtube/channels/list/", YouTubeChannelsList.as_view(), name='async_youtube_channels'),
    url(r'youtube/webhook/event/', YouTubeWebhookEvent.as_view(), name='youtube_webhook_event'),

    # ZohoCRM
    url(r"async/zohocrm/module/list/", ZohoCRMModuleList.as_view(), name='async_zohorcrm_modules'),

    # Salesforce
    url(r"async/salesforce/sobjects/list/", SalesforceSObjectList.as_view(), name='async_salesforce_sobjects'),
    url(r"async/salesforce/event/list/", SalesforceEventList.as_view(), name='async_salesforce_events'),
    url(r"salesforce/webhook/event/", SalesforceWebhookEvent.as_view(), name='async_salesforce_events'),
]
