from django.apps import AppConfig

APP_NAME = 'gp'


class GPConfig(AppConfig):
    name = 'apps.%s' % APP_NAME

    def ready(self):
        import apps.gp.signals
