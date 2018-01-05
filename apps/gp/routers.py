class DefaultRouter(object):
    """

    """

    def db_for_read(self, model, **kwargs):
        if model._meta.app_label in ['gp', 'auth', 'contenttypes', 'account', 'admin', 'sessions', 'sites',
                                     'socialaccount']:
            return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label in ['gp', 'auth', 'contenttypes', 'account', 'admin', 'sessions', 'sites',
                                     'socialaccount']:
            return 'default'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        if obj1._state.db == 'default' or obj2._state.db == 'default':
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label in ['gp', 'auth', 'contenttypes', 'account', 'admin', 'sessions', 'sites', 'socialaccount']:
            return db == 'default'
        return None


class HistoryRouter(object):
    """

    """

    def db_for_read(self, model, **kwargs):
        if model._meta.app_label == "history":
            return 'history'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == "history":
            return 'history'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        if obj1._state.db == 'history' or obj2._state.db == 'history':
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == 'history':
            return db == 'history'
        return None


class LandingRouter(object):
    """

    """

    def db_for_read(self, model, **kwargs):
        if model._meta.app_label == "landing":
            return 'landing'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == "landing":
            return 'landing'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        if obj1._state.db == 'landing' or obj2._state.db == 'landing':
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == 'landing':
            return db == 'landing'
        return None


class BillingRouter(object):
    """

    """

    def db_for_read(self, model, **kwargs):
        if model._meta.app_label == "billing":
            return 'billing'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == "billing":
            return 'billing'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        if obj1._state.db == 'billing' or obj2._state.db == 'billing':
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == 'billing':
            return db == 'billing'
        return None
