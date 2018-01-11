from django.apps import AppConfig

APP_NAME = 'billing'


class BillingConfig(AppConfig):
    name = 'apps.%s' % APP_NAME

    def ready(self):
        import apps.billing.signals
