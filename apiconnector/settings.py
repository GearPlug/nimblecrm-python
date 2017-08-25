import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRET_KEY = 'nd65g3a23c!y%+a_%+v)!trnjh%c=gh(zg5!gsn*qo&b6*nsbb'
DEBUG = True # False
CURRENT_HOST = "https://localhost"
ALLOWED_HOSTS = [CURRENT_HOST, '*', ]
CORS_ORIGIN_ALLOW_ALL = True
SITE_ID = 1

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    # 3rd
    'django_uwsgi',
    'account',
    'django_forms_bootstrap',
    'oauth2_provider',
    'rest_framework',
    'widget_tweaks',
    'debug_toolbar',
    'facebook',
    'extra_views',
    #
    'apps.wizard',
    'apps.home',
    'apps.user',
    'apps.gear',
    'apps.plug',
    'apps.connection',
    'apps.gp',

]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    # 'account.middleware.LocaleMiddleware',  # account app
    # 'account.middleware.TimezoneMiddleware',  # account app
]

ROOT_URLCONF = 'apiconnector.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['templates', ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                "account.context_processors.account",
            ],
        },
    },
]

WSGI_APPLICATION = 'apiconnector.wsgi.application'

DATABASES = {
    # 'default': {
    #     'ENGINE': 'django.db.backends.sqlite3',
    #     'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    # },
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'OPTIONS': {
            'read_default_file': os.path.join(BASE_DIR, 'apiconnector/mysql.cnf', )
        },
    },
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator', },
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', },
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator', },
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator', },
]

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'log/django/debug.log',
        },
    },
    'loggers': {
        'django.server': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
        'server': {
            'formar': '%(message)s'
        }
    },
    'handlers': {
        'controller.file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'log/controller/general.log'),
            'maxBytes': 1024 * 1024 * 5,  # 5 MB
            'backupCount': 50,
            'formatter': 'verbose',
        },
        'request.file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'log/django/request.log'),
            'maxBytes': 1024 * 1024 * 5,  # 5 MB
            'backupCount': 2,
            'formatter': 'server',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'console.server': {
            'class': 'logging.StreamHandler',
            'formatter': 'server',
        },
        'controller': {
            'level': 'INFO',
            'class': 'apps.gp.handlers.DBHandler',
            'model': 'apps.gp.models.ControllerLog',
            'expiry': 86400,
            'formatter': 'server',
        },
    },
    'loggers': {
        'django.server': {
            'handlers': ['request.file', ],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
    }
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'staticfiles'),
]

AUTHENTICATION_BACKENDS = [
    'account.auth_backends.EmailAuthenticationBackend', ]

# account app
ACCOUNT_EMAIL_UNIQUE = True
ACCOUNT_EMAIL_CONFIRMATION_REQUIRED = False


def ACCOUNT_USER_DISPLAY(user): return user.email


ACCOUNT_LOGIN_REDIRECT_URL = '/dashboard/'
ACCOUNT_SIGNUP_REDIRECT_URL = '/dashboard/'

# SETTINGS CENTRALIZADOS
# Facebook
FACEBOOK_APP_ID = '1860382657578411'
FACEBOOK_APP_SECRET = '3ce16acabb2efeda4336e4e5f9576d8b'
FACEBOOK_GRAPH_VERSION = '2.7'

# Email
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_USE_TLS = True
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
EMAIL_PORT = 587

# Slack
SLACK_CLIENT_ID = '129041278545.209366736883'
SLACK_CLIENT_SECRET = '8a78615be489b8314702c0d67f159ddd'
SLACK_PERMISSIONS_URL = 'https://slack.com/oauth/authorize?client_id={0}&scope=team:read,channels:read,chat:write:bot,im:history,im:read'.format(
    SLACK_CLIENT_ID)

# Google (Gustavo)
GOOGLE_CLIENT_ID = '278354320502-6ptllif5k11cn8uskm8aotp6fqb2g7dr.apps.googleusercontent.com'
GOOGLE_CLIENT_SECRET = 'LgJ2hrSVu_lmAJkJhwzgfiDG'
GOOGLE_AUTH_CALLBACK_URL = '{0}/connection/auth-callback/google/'.format(CURRENT_HOST)

# Twitter
TWITTER_CLIENT_ID = '72ceIxo0vh6IUvPEzRLwU63dK'
TWITTER_CLIENT_SECRET = 'oRpX6077A1spuOl36JVgupAwhF2ZuYmfL9Dk1WB3OxqkCNtw0N'

# SurveyMonkey
SURVEYMONKEY_CLIENT_ID = "aSrDRChrQjqy--JCMHiPDw"
SURVEYMONKEY_CLIENT_SECRET = "99572991333427996854184255528563883257"
SURVEYMONKEY_API_BASE = "https://api.surveymonkey.net"
SURVEYMONKEY_AUTH_CODE_ENDPOINT = "/oauth/authorize"
SURVEYMONKEY_ACCESS_TOKEN_ENDPOINT = "/oauth/token"
SURVEYMONKEY_REDIRECT_URI = "{0}/connection/auth-callback/surveymonkey/".format(CURRENT_HOST)

# Instagram
INSTAGRAM_CLIENT_ID = '17e2105451294cd6a372233f25e2c6ec'
INSTAGRAM_CLIENT_SECRET = '6f8a7fb1ac0c4cada3c01d88561d35f6'
INSTAGRAM_AUTH_URL = '{0}/connection/auth-callback/instagram/'.format(CURRENT_HOST)
INSTAGRAM_SCOPE = ['basic']
INSTAGRAM_AUTH_REDIRECT_URL = 'connection:instagram_auth_success_create_connection'

# YouTube
YOUTUBE_API_KEY = 'XXXXXXXXXXXX'

# SalesForce
SALESFORCE_CLIENT_ID = '3MVG9CEn_O3jvv0w0NDdh1QNjan9zEmgVh3F6Mxsuyq4NUo.InTWMLG4ayz5mlCxTw7eWvlKR.PmtOdTladnW'
SALESFORCE_CLIENT_SECRET = '1338285709176181412'
SALESFORCE_REQUEST_TOKEN_URL = 'https://login.salesforce.com/services/oauth2/token'
SALESFORCE_ACCESS_TOKEN_URL = 'https://login.salesforce.com/services/oauth2/token'
SALESFORCE_AUTHORIZE_URL = 'https://login.salesforce.com/services/oauth2/authorize'
SALESFORCE_REDIRECT_URI = '{0}/connection/auth-callback/salesforce/'.format(CURRENT_HOST)

# Hubspot
HUBSPOT_REDIRECT_URI = "{0}/connection/auth-callback/hubspot/".format(CURRENT_HOST)
HUBSPOT_CLIENT_ID = "633af850-f08a-42e5-a6e7-da65a177bcd5"
HUBSPOT_CLIENT_SECRET = "94e688b7-9390-4b59-a6df-151eac348e89"

# Evernote
EVERNOTE_CONSUMER_KEY = "ltorres-6238"
EVERNOTE_CONSUMER_SECRET = "a4673a77baca5424"
EVERNOTE_REDIRECT_URL = "{0}/connection/auth-callback/evernote/".format(CURRENT_HOST)

# Shopify
SHOPIFY_API_KEY = "0eef989bfc56004265e4a8c4e699fd2e"
SHOPIFY_API_KEY_SECRET = "aa53f3fcd4f635317e3c67b61a067356"
SHOPIFY_REDIRECT_URI = "{0}/connection/auth-callback/shopify/".format(CURRENT_HOST)
SHOPIFY_SCOPE = "read_products, write_products, read_orders, read_customers, write_orders, write_customers"

# Asana
ASANA_CLIENT_ID = '385400269218379'
ASANA_CLIENT_SECRET = 'b06634b490e0408d8f575e38a2d7e7f3'
ASANA_REDIRECT_URL = '{0}/connection/auth-callback/asana/'.format(CURRENT_HOST)
ASANA_WEBHOOK_URL = ''

# Mercadolibre

MERCADOLIBRE_CLIENT_ID = '1063986061828245'
MERCADOLIBRE_CLIENT_SECRET = 'MyDv8rmoWjJneTgkxEhp3QRONbUp3CPV'
MERCADOLIBRE_REDIRECT_URL = '{0}/connection/auth-callback/mercadolibre/'.format(CURRENT_HOST)

# Wunderlist
WUNDERLIST_CLIENT_ID = 'c68a87efca8b22d50fee'
WUNDERLIST_CLIENT_SECRET = '8a60113066eb052463be8e1d7414edb8a2f57d2f4cd118b82fb201820c8c'
WUNDERLIST_REDIRECT_URL = '{0}/connection/auth-callback/wunderlist/'.format(CURRENT_HOST)
