SECRET_KEY = 'nd65g3a23c!y%+a_%+v)!trnjh%c=gh(zg5!gsn*qo&b6*nsbb'
DEBUG = True
CURRENT_HOST_PROTOCOL = "http"
CURRENT_HOST_NAME = "127.0.0.1:8000"
CURRENT_HOST = "{0}://{1}".format(CURRENT_HOST_PROTOCOL, CURRENT_HOST_NAME)
ALLOWED_HOSTS = [CURRENT_HOST, '*', ]
# INTERNAL_IPS = ['127.0.0.1', ]
WEBHOOK_HOST = CURRENT_HOST

# EMAIL
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_USE_TLS = True
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'usuario@gmail.com'
EMAIL_HOST_PASSWORD = 'password-de-gmail'
DEFAULT_FROM_EMAIL = 'noreply@grplug.com'
CONTACT_EMAIL = ['support@grplug.com']
