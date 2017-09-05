from django.conf.urls import url
from apps.connection.views import CreateConnectionView, ListConnectionView, ListConnectorView, AuthSuccess, \
    TestConnectionView, CreateConnectionSuccessView, CreateTokenAuthorizedConnectionView, \
    GoogleAuthView, SlackAuthView, TwitterAuthView, SurveyMonkeyAuthView, InstagramAuthView, SalesforceAuthView, \
    ShopifyAuthView, EvernoteAuthView, AsanaAuthView, MercadoLibreAuthView, WunderListAuthView, HubspotAuthView, \
    AjaxMercadoLibrePostSiteView, ManageConnectionView, MailchimpAuthView, GitLabAuthView  # ,AJAXGetSurveyListView


urlpatterns = [
    # Create Connection
    url(r'create/(?P<connector_id>\d+)/$', CreateConnectionView.as_view(), name='create'),
    # Create Success
    url(r'create/success/$', CreateConnectionSuccessView.as_view(), name='create_success'),
    # Test Connection
    url(r'^test/(?P<connector_id>\d+)/$', TestConnectionView.as_view(), name="test"),
    # Connection list
    url(r'^list/(?P<connector_id>\d+)/(?P<type>(source|target)+)/$', ListConnectionView.as_view(),
        name='list'),
    # List Connectors
    url(r'^list/connector/(?P<type>(source|target)+)/$', ListConnectorView.as_view(), name='connector_list'),

    url(r'manage/', ManageConnectionView.as_view(), name="manage"),

    # Auth Callbacks
    url(r'^auth-callback/slack/', SlackAuthView.as_view(), name="slack_auth"),
    url(r'^auth-callback/google/', GoogleAuthView.as_view(), name="google_auth"),
    url(r'^auth-callback/asana/', AsanaAuthView.as_view(), name="asana_auth"),
    url(r'^auth-callback/wunderlist/', WunderListAuthView.as_view(), name="wunderlist_auth"),
    url(r'^auth-callback/twitter/', TwitterAuthView.as_view(), name="twitter_auth"),
    url(r'^auth-callback/hubspot/', HubspotAuthView.as_view(), name="hubspot_auth"),
    url(r'^auth-callback/instagram/', InstagramAuthView.as_view(), name="instagram_auth"),
    url(r'^auth-callback/salesforce/', SalesforceAuthView.as_view(), name="salesforce_auth"),
    url(r'^auth-callback/surveymonkey/', SurveyMonkeyAuthView.as_view(), name="surveymonkey_auth"),
    url(r'^auth-callback/evernote/', EvernoteAuthView.as_view(), name="evernote_auth"),
    url(r'^auth-callback/salesforce/', SalesforceAuthView.as_view(), name="salesforce_auth"),
    url(r'^auth-callback/shopify/', ShopifyAuthView.as_view(), name="shopify_auth"),
    url(r'^auth-callback/mercadolibre/', MercadoLibreAuthView.as_view(), name="mercadolibre_auth"),
    url(r'^auth-callback/gitlab/', GitLabAuthView.as_view(), name="gitlab_auth"),
    url(r'^auth-callback/mailchimp/', MailchimpAuthView.as_view(), name="mailchimp_auth"),
    # Create Authorizated Connection
    url(r'^create/authorizated/', CreateTokenAuthorizedConnectionView.as_view(),
        name="create_token_authorized_connection"),

    # MercadoLibre
    url(r"^ajax/mercadolibre/post/site/$", AjaxMercadoLibrePostSiteView.as_view(),
        name="ajax_mercadolibre_post_site"),

    # AuthSuccess
    url(r'^auth/success/$', AuthSuccess.as_view(), name="auth_sucess"),
]
