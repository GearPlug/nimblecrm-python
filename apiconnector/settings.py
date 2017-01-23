import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRET_KEY = 'nd65g3a23c!y%+a_%+v)!trnjh%c=gh(zg5!gsn*qo&b6*nsbb'
DEBUG = True
ALLOWED_HOSTS = ['*', ]
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
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]
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
        'controller': {
            'handlers': ['controller', ],
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

#
CORS_ORIGIN_ALLOW_ALL = True

# SETTINGS CENTRALIZADOS
# Facebook
FACEBOOK_APP_ID = '1731160853833926'
FACEBOOK_APP_SECRET = '0e6b58b4982c602374c13fb47c418805'
FACEBOOK_GRAPH_VERSION = '2.6'

# CELERY STUFF
BROKER_URL = 'redis://localhost:6379'
CELERY_RESULT_BACKEND = 'redis://localhost:6379'
# BROKER_URL = 'amqp://guest:guest@localhost:5672//'
# CELERY_RESULT_BACKEND = 'amqp://guest:guest@localhost:5672//'
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'America/Bogota'

# Email
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_USE_TLS = True
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_HOST_USER = 'gsaavedra@grplug.com'
EMAIL_HOST_PASSWORD = ''
EMAIL_PORT = 587
