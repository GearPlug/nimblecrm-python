from django.conf.urls import url
from apps.connection.views import CreateConnectionView, ListConnectorView, GoogleAuthView, \
    GoogleAuthSuccessView, SlackAuthView, AuthSuccess, TwitterAuthView, \
    TwitterAuthSuccessCreateConnection, SurveyMonkeyAuthView, SurveyMonkeyAuthSuccessCreateConnection, \
    InstagramAuthView, InstagramAuthSuccessCreateConnection, SalesforceAuthView, \
    SalesforceAuthSuccessCreateConnection, ShopifyAuthView, ShopifyAuthSuccessCreateConnection, TestConnectionView, \
    CreateConnectionSuccessView, HubspotAuthView, HubspotAuthSuccessCreateConnection, EvernoteAuthView, \
    EvernoteAuthSuccessCreateConnection, AsanaAuthView, CreateTokenAuthorizedConnectionView, MercadoLibreAuthView, \
    MercadoLibreAuthSuccessCreateConnection, AjaxMercadoLibrePostSiteView, WunderListAuthView #,AJAXGetSurveyListView

from apps.gp.enum import GoogleAPIEnum

urlpatterns = [
    # Create Connection
    url(r'create/(?P<connector_id>\d+)/$', CreateConnectionView.as_view(), name='create'),
    # Create Success
    url(r'create/success/$', CreateConnectionSuccessView.as_view(), name='create_success'),
    # Test Connection
    url(r'^test/(?P<connector_id>\d+)/$', TestConnectionView.as_view(), name="test"),
    # List Connectors
    url(r'list/connector/$', ListConnectorView.as_view(), name='list_connector'),

    # Auth Callbacks
    url(r'^auth-callback/slack/', SlackAuthView.as_view(), name="slack_auth"),
    url(r'^auth-callback/google/', GoogleAuthView.as_view(), name="google_auth"),
    url(r'^auth-callback/facebook/', GoogleAuthView.as_view(), name="facebook_auth"),
    url(r'^auth-callback/asana/', AsanaAuthView.as_view(), name="asana_auth"),
    url(r'^auth-callback/wunderlist/', WunderListAuthView.as_view(), name="wunderlist_auth"),

    # Auth Success
    url(r'^auth/google/success/$', GoogleAuthSuccessView.as_view(),
        {'api': GoogleAPIEnum.GoogleSpreadSheets},
        name='google_auth_success'),

    # Create Authorizated Connection
    url(r'^create/authorizated/', CreateTokenAuthorizedConnectionView.as_view(), name="create_token_authorized_connection"),

    # Twitter
    url(r"^twitter_auth/$", TwitterAuthView.as_view(), name="twitter_auth"),
    url(r"^twitter_auth/success/$", TwitterAuthSuccessCreateConnection.as_view(),
        name="twitter_auth_success_create_connection"),

    # Hubspot
    url(r"^hubspot_auth/$", HubspotAuthView.as_view(), name="hubspot_auth"),
    url(r"^hubspot_auth/success/$", HubspotAuthSuccessCreateConnection.as_view(),
        name="hubspot_auth_success_create_connection"),

    # Instagram
    url(r"^instagram_auth/$", InstagramAuthView.as_view(), name="instagram_auth"),
    url(r"^instagram_auth/success/$", InstagramAuthSuccessCreateConnection.as_view(),
        name="instagram_auth_success_create_connection"),

    # SalesForce
    url(r"^salesforce_auth/$", SalesforceAuthView.as_view(), name="salesforce_auth"),
    url(r"^salesforce_auth/success/$", SalesforceAuthSuccessCreateConnection.as_view(),
        name="salesforce_auth_success_create_connection"),

    # surveymonkey
    url(r"^survey_monkey_auth/$", SurveyMonkeyAuthView.as_view(), name="survey_monkey_auth"),
    url(r"^survey_monkey_auth/success/$", SurveyMonkeyAuthSuccessCreateConnection.as_view(),
        name="survey_monkey_auth_success_create_connection"),

    # evernote
    url(r"^evernote_auth/$", EvernoteAuthView.as_view(), name="evernote_auth"),
    url(r"^evernote_auth/success/$", EvernoteAuthSuccessCreateConnection.as_view(),
        name="evernote_success_create_connection"),

    # shopify
    url(r"^shopify_auth/$", ShopifyAuthView.as_view(), name="shopify_auth"),
    url(r"^shopify_auth/success/$", ShopifyAuthSuccessCreateConnection.as_view(),
        name="shopify_auth_success_create_connection"),

    # Slack

    # MercadoLibre
    url(r"^mercadolibre_auth/$", MercadoLibreAuthView.as_view(), name="mercadolibre_auth"),
    url(r"^mercadolibre_auth/success/$", MercadoLibreAuthSuccessCreateConnection.as_view(),
        name="mercadolibre_auth_success_create_connection"),
    url(r"^ajax/mercadolibre/post/site/$", AjaxMercadoLibrePostSiteView.as_view(),
        name="ajax_mercadolibre_post_site"),

    # AuthSuccess
    url(r'^auth/success/$', AuthSuccess.as_view(), name="auth_sucess"),
]
