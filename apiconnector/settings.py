import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRET_KEY = 'nd65g3a23c!y%+a_%+v)!trnjh%c=gh(zg5!gsn*qo&b6*nsbb'
DEBUG = True
ALLOWED_HOSTS = ['*', ]
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

AUTHENTICATION_BACKENDS = ['account.auth_backends.EmailAuthenticationBackend', ]

# account app
ACCOUNT_EMAIL_UNIQUE = True
ACCOUNT_EMAIL_CONFIRMATION_REQUIRED = True
ACCOUNT_USER_DISPLAY = lambda user: user.email
ACCOUNT_LOGIN_REDIRECT_URL = '/dashboard/'
ACCOUNT_SIGNUP_REDIRECT_URL = '/dashboard/'

# SETTINGS CENTRALIZADOS
# Facebook
FACEBOOK_APP_ID = '1860382657578411'
FACEBOOK_APP_SECRET = '3ce16acabb2efeda4336e4e5f9576d8b'

FACEBOOK_GRAPH_VERSION = '2.6'

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
SLACK_PERMISSIONS_URL = 'https://slack.com/oauth/authorize?client_id={0}&scope=team:read,channels:read,chat:write:bot,im:history,im:read'.format(SLACK_CLIENT_ID)

# Google (Gustavo)
GOOGLE_CLIENT_ID = '278354320502-6ptllif5k11cn8uskm8aotp6fqb2g7dr.apps.googleusercontent.com'
GOOGLE_CLIENT_SECRET = 'LgJ2hrSVu_lmAJkJhwzgfiDG'

# Twitter
TWITTER_CLIENT_ID = 'D5ZJJmF11n9Sp8E9p7GRGhpiR'
TWITTER_CLIENT_SECRET = '0RIWtTgeSfOmsIO10MYyFCU4BQhuoISgShAreYy3RHyeQCd5vb'

# SurveyMonkey
SURVEYMONKEY_CLIENT_ID = "QIMqiHnrRvuzCFAmlTNOkA"
SURVEYMONKEY_CLIENT_SECRET = "17068417592671949424384618935059383185"
SURVEYMONKEY_REDIRECT_URI = "https://l.grplug.com/connection/survey_monkey_auth/"
SURVEYMONKEY_API_BASE = "https://api.surveymonkey.net"
SURVEYMONKEY_AUTH_CODE_ENDPOINT = "/oauth/authorize"
SURVEYMONKEY_ACCESS_TOKEN_ENDPOINT = "/oauth/token"

# Instagram
INSTAGRAM_CLIENT_ID = 'xxxxxxxx'
INSTAGRAM_CLIENT_SECRET = 'yyyyyyyyy'


# YouTube
YOUTUBE_API_KEY = 'XXXXXXXXXXXX'

# SalesForce
SALESFORCE_CLIENT_ID = ''
SALESFORCE_CLIENT_SECRET = ''
SALESFORCE_REQUEST_TOKEN_URL = 'https://login.salesforce.com/services/oauth2/token'
SALESFORCE_ACCESS_TOKEN_URL = 'https://login.salesforce.com/services/oauth2/token'
SALESFORCE_REDIRECT_URI = ''
SALESFORCE_AUTHORIZE_URL = 'https://login.salesforce.com/services/oauth2/authorize'
SALESFORCE_WEBHOOK_URI = ''

#Shopify
SHOPIFY_SHOP_URL="my-first-project-2017"
SHOPIFY_API_KEY="8058ebd552b2ba23d9d1c6221b514fab"
SHOPIFY_API_KEY_SECRET="d32f6b242ddaa2dd2b29bf3eb329a1c5"
SHOPIFY_REDIRECT_URI="http://127.0.0.1:8000/connection/shopify_auth/"

#Hubspot
HUBSPOT_REDIRECT_URI="https://87b30496.ngrok.io/connection/hubspot_auth/"
HUBSPOT_CLIENT_ID="633af850-f08a-42e5-a6e7-da65a177bcd5"
HUBSPOT_CLIENT_SECRET="94e688b7-9390-4b59-a6df-151eac348e89"

#Evernote
EVERNOTE_CONSUMER_KEY="ltorres-6238"
EVERNOTE_CONSUMER_SECRET="a4673a77baca5424"
EVERNOTE_REDIRECT_URL="http://127.0.0.1:8000/connection/evernote_auth/"


# Asana
ASANA_CLIENT_ID = '385400269218379'
ASANA_CLIENT_SECRET = 'b06634b490e0408d8f575e38a2d7e7f3'
ASANA_REDIRECT_URL = 'https://26677b10.ngrok.io/connection/auth-callback/asana/'
ASANA_WEBHOOK_URL = ''

# Mercadolibre
MERCADOLIBRE_CLIENT_ID=''
MERCADOLIBRE_CLIENT_SECRET=''
MERCADOLIBRE_REDIRECT_URL='https://9d25c5df.ngrok.io/connection/mercadolibre_auth/'

