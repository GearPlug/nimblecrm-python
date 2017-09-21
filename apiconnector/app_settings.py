import os
from dotenv.main import load_dotenv

try:
    from .local_settings import CURRENT_HOST
except ImportError as e:
    from .production_settings import CURRENT_HOST

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

# Facebook
FACEBOOK_APP_ID = os.environ.get('FACEBOOK_APP_ID')
FACEBOOK_APP_SECRET = os.environ.get('FACEBOOK_APP_SECRET')
FACEBOOK_GRAPH_VERSION = '2.10'

# Slack
SLACK_CLIENT_ID = os.environ.get('SLACK_CLIENT_ID')
SLACK_CLIENT_SECRET = os.environ.get('SLACK_CLIENT_SECRET')
SLACK_PERMISSIONS_URL = 'https://slack.com/oauth/authorize?client_id={0}&scope=team:read,channels:read,' \
                        'chat:write:bot,im:history,im:read'.format(SLACK_CLIENT_ID)

# Google
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
GOOGLE_AUTH_CALLBACK_URL = '{0}/connection/auth-callback/google/'.format(CURRENT_HOST)

# Twitter
TWITTER_CLIENT_ID = os.environ.get('TWITTER_CLIENT_ID')
TWITTER_CLIENT_SECRET = os.environ.get('TWITTER_CLIENT_SECRET')

# SurveyMonkey
SURVEYMONKEY_CLIENT_ID = os.environ.get('SURVEYMONKEY_CLIENT_ID')
SURVEYMONKEY_CLIENT_SECRET = os.environ.get('SURVEYMONKEY_CLIENT_ID')
SURVEYMONKEY_API_BASE = "https://api.surveymonkey.net"
SURVEYMONKEY_AUTH_CODE_ENDPOINT = "/oauth/authorize"
SURVEYMONKEY_ACCESS_TOKEN_ENDPOINT = "/oauth/token"
SURVEYMONKEY_REDIRECT_URI = "{0}/connection/auth-callback/surveymonkey/".format(CURRENT_HOST)

# Instagram
INSTAGRAM_CLIENT_ID = os.environ.get('INSTAGRAM_CLIENT_ID')
INSTAGRAM_CLIENT_SECRET = os.environ.get('INSTAGRAM_CLIENT_SECRET')
INSTAGRAM_AUTH_URL = '{0}/connection/auth-callback/instagram/'.format(CURRENT_HOST)
INSTAGRAM_SCOPE = ['basic']
INSTAGRAM_AUTH_REDIRECT_URL = 'connection:instagram_auth_success_create_connection'

# SalesForce
SALESFORCE_CLIENT_ID = os.environ.get('SALESFORCE_CLIENT_ID')
SALESFORCE_CLIENT_SECRET = os.environ.get('SALESFORCE_CLIENT_SECRET')
SALESFORCE_REQUEST_TOKEN_URL = 'https://login.salesforce.com/services/oauth2/token'
SALESFORCE_ACCESS_TOKEN_URL = 'https://login.salesforce.com/services/oauth2/token'
SALESFORCE_AUTHORIZE_URL = 'https://login.salesforce.com/services/oauth2/authorize'
SALESFORCE_REDIRECT_URI = '{0}/connection/auth-callback/salesforce/'.format(CURRENT_HOST)

# Hubspot
HUBSPOT_CLIENT_ID = os.environ.get('HUBSPOT_CLIENT_ID')
HUBSPOT_CLIENT_SECRET = os.environ.get('HUBSPOT_CLIENT_SECRET')
HUBSPOT_REDIRECT_URI = "{0}/connection/auth-callback/hubspot/".format(CURRENT_HOST)

# Evernote
EVERNOTE_CONSUMER_KEY = os.environ.get('EVERNOTE_CONSUMER_KEY')
EVERNOTE_CONSUMER_SECRET = os.environ.get('EVERNOTE_CONSUMER_SECRET')
EVERNOTE_REDIRECT_URL = "{0}/connection/auth-callback/evernote/".format(CURRENT_HOST)

# Shopify
SHOPIFY_API_KEY = os.environ.get('SHOPIFY_API_KEY')
SHOPIFY_API_KEY_SECRET = os.environ.get('SHOPIFY_API_KEY_SECRET')
SHOPIFY_REDIRECT_URI = "{0}/connection/auth-callback/shopify/".format(CURRENT_HOST)
SHOPIFY_SCOPE = "read_products, write_products, read_orders, read_customers, write_orders, write_customers"

# Asana
ASANA_CLIENT_ID = os.environ.get('ASANA_CLIENT_ID')
ASANA_CLIENT_SECRET = os.environ.get('ASANA_CLIENT_SECRET')
ASANA_REDIRECT_URL = '{0}/connection/auth-callback/asana/'.format(CURRENT_HOST)
ASANA_WEBHOOK_URL = '??'  # TODO CHECK

# Mercadolibre
MERCADOLIBRE_CLIENT_ID = os.environ.get('MERCADOLIBRE_CLIENT_ID')
MERCADOLIBRE_CLIENT_SECRET = os.environ.get('MERCADOLIBRE_CLIENT_SECRET')
MERCADOLIBRE_REDIRECT_URL = '{0}/connection/auth-callback/mercadolibre/'.format(CURRENT_HOST)

# Wunderlist
WUNDERLIST_CLIENT_ID = os.environ.get('WUNDERLIST_CLIENT_ID')
WUNDERLIST_CLIENT_SECRET = os.environ.get('WUNDERLIST_CLIENT_SECRET')
WUNDERLIST_REDIRECT_URL = '{0}/connection/auth-callback/wunderlist/'.format(CURRENT_HOST)

# GitLab
GITLAB_CLIENT_ID = os.environ.get('GITLAB_CLIENT_ID')
GITLAB_CLIENT_SECRET = os.environ.get('GITLAB_CLIENT_SECRET')
GITLAB_REDIRECT_URL = '{0}/connection/auth-callback/gitlab/'.format(CURRENT_HOST)
GITLAB_REFRESH_URL = "https://gitlab.com/oauth/token"
GITLAB_PROTECT_URL = "https://gitlab.com/api/v4/user"

# MailChimp
MAILCHIMP_CLIENT_ID = os.environ.get('MAILCHIMP_CLIENT_ID')
MAILCHIMP_CLIENT_SECRET = os.environ.get('MAILCHIMP_CLIENT_SECRET')
MAILCHIMP_REDIRECT_URL = '{0}/connection/auth-callback/mailchimp/'.format(CURRENT_HOST)
MAILCHIMP_ACCESS_TOKEN_URI = 'https://login.mailchimp.com/oauth2/token'
