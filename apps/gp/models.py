from django.db import models
from django.contrib import admin
from apps.gp.model_fields import JSONField
from apps.user.models import User

connections = ['connection_facebook', 'connection_mysql', 'connection_sugarcrm', 'connection_mailchimp',
               'connection_google_sheets']


class Connector(models.Model):
    name = models.CharField('name', max_length=120)
    is_active = models.BooleanField('is active', default=False)
    css_class = models.CharField('css class', max_length=40)
    is_source = models.BooleanField('is source', default=False)
    is_target = models.BooleanField('is target', default=False)

    class Meta:
        verbose_name = 'connector'

    def __str__(self):
        return self.name


class Action(models.Model):
    ACTION_TYPE = (('source', 'Source'), ('target', 'Target'))
    connector = models.ForeignKey(Connector, on_delete=models.CASCADE, related_name='action')
    action_type = models.CharField(choices=ACTION_TYPE, max_length=7, default='source')
    name = models.CharField('name', max_length=120)
    description = models.CharField('description', max_length=300)
    is_active = models.BooleanField('is active', default=False)

    @property
    def is_source(self):
        return self.action_type == 'source'

    @property
    def is_target(self):
        return self.action_type == 'target'

    def __str__(self):
        return self.name


class ActionSpecification(models.Model):
    action = models.ForeignKey(Action, on_delete=models.CASCADE, related_name='action_specification')
    name = models.CharField('name', max_length=30)

    def __str__(self):
        return self.action.name + ': ' + self.name


class Connection(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    connector = models.ForeignKey(Connector, default=2, on_delete=models.CASCADE)
    created = models.DateTimeField('created', auto_now_add=True)
    last_update = models.DateTimeField('last update', auto_now=True)
    is_deleted = models.BooleanField('is deleted', default=False)

    @property
    def name(self):
        available_connections = connections
        for con in available_connections:
            if hasattr(self, con):
                return str(getattr(self, con))
        return 'Object not found'

    @property
    def related_id(self):
        available_connections = connections
        for con in available_connections:
            if hasattr(self, con):
                return str(getattr(self, con).id)
        return 'Object not found'

    @property
    def related_connection(self):
        available_connections = connections
        for con in available_connections:
            if hasattr(self, con):
                return getattr(self, con)
        return 'Object not found'

    def __str__(self):
        return '%s' % self.name


class FacebookConnection(models.Model):
    connection = models.OneToOneField(Connection, on_delete=models.CASCADE, related_name='connection_facebook')
    name = models.CharField('name', max_length=200)
    id_page = models.CharField('id page', max_length=300)
    id_form = models.CharField('id form', max_length=300)
    token = models.CharField('token', max_length=300)

    def __str__(self):
        return self.name


class MySQLConnection(models.Model):
    connection = models.OneToOneField(Connection, on_delete=models.CASCADE, related_name='connection_mysql')
    name = models.CharField('name', max_length=200)
    host = models.CharField('host', max_length=200)
    database = models.CharField('database', max_length=200)
    table = models.CharField('table', max_length=200)
    port = models.CharField('port', max_length=7)
    connection_user = models.CharField('user', max_length=60)
    connection_password = models.CharField('password', max_length=40)

    def __str__(self):
        return self.name


class SugarCRMConnection(models.Model):
    connection = models.OneToOneField(Connection, on_delete=models.CASCADE, related_name='connection_sugarcrm')
    name = models.CharField('name', max_length=200)
    url = models.CharField('url', max_length=200)
    connection_user = models.CharField('user', max_length=200)
    connection_password = models.CharField('password', max_length=200)

    def __str__(self):
        return self.name


class MailChimpConnection(models.Model):
    connection = models.OneToOneField(Connection, on_delete=models.CASCADE, related_name='connection_mailchimp')
    name = models.CharField('name', max_length=200)
    connection_user = models.CharField('user', max_length=200)
    api_key = models.CharField('api key', max_length=200)

    def __str__(self):
        return self.name


class GoogleSpreadSheetsConnection(models.Model):
    connection = models.OneToOneField(Connection, on_delete=models.CASCADE, related_name='connection_google_sheets')
    name = models.CharField('name', max_length=200)
    credentials_json = JSONField(blank=True, null=True)


class Plug(models.Model):
    ACTION_TYPE = (('source', 'Source'), ('target', 'Target'))
    name = models.CharField('name', max_length=120)
    connection = models.ForeignKey(Connection, null=True, on_delete=models.CASCADE, related_name='plug')
    action = models.ForeignKey(Action, null=True, on_delete=models.CASCADE)
    plug_type = models.CharField(choices=ACTION_TYPE, max_length=7, default='source')
    user = models.ForeignKey(User)
    is_active = models.BooleanField('is active', default=False)
    created = models.DateTimeField('created', auto_now_add=True)
    last_update = models.DateTimeField('last update', auto_now=True)

    @property
    def is_source(self):
        return self.plug_type == 'source'

    @property
    def is_target(self):
        return self.plug_type == 'target'

    def __str__(self):
        return self.name


class PlugSpecification(models.Model):
    plug = models.ForeignKey(Plug, on_delete=models.CASCADE, related_name='plug_specification')
    action_specification = models.ForeignKey(ActionSpecification)
    value = models.CharField('value', max_length=1000)

    class Meta:
        unique_together = ['plug', 'action_specification']


class StoredData(models.Model):
    plug = models.ForeignKey(Plug, related_name='stored_data')
    connection = models.ForeignKey(Connection, related_name='stored_data')
    name = models.CharField('name', max_length=300)
    value = models.CharField('value', max_length=3000, default='', blank=True)
    datetime = models.DateTimeField(auto_now_add=True)
    object_id = models.CharField('object_id', max_length=50, null=True)

    def __str__(self):
        return '%s %s %s' % (self.id, self.name, self.object_id)


class Gear(models.Model):
    name = models.CharField('name', max_length=120)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    source = models.ForeignKey(Plug, null=True, on_delete=models.SET_NULL, related_name='source_gear')
    target = models.ForeignKey(Plug, null=True, on_delete=models.SET_NULL, related_name='target_gear')
    is_active = models.BooleanField('is active', default=False)
    created = models.DateTimeField('created', auto_now_add=True)
    last_update = models.DateTimeField('last update', auto_now=True)

    @property
    def is_running(self):
        return self.is_active and self.gear_map.is_active


class GearMap(models.Model):
    gear = models.OneToOneField(Gear, related_name='gear_map')
    created = models.DateTimeField('created', auto_now_add=True)
    last_update = models.DateTimeField('last update', auto_now=True)
    is_active = models.BooleanField('is active', default=True)
    last_sent_stored_data = models.ForeignKey(StoredData, related_name='gear_map', null=True, default=None,
                                              on_delete=models.SET_NULL)
    last_sent_stored_data_creation_date = models.DateTimeField('last sent storeddata creation date', null=True,
                                                               default=None)
    last_source_update = models.DateTimeField(null=True, default=None)
    created = models.DateTimeField('created', auto_now_add=True)

    class Meta:
        unique_together = ['id', 'gear']


class GearMapData(models.Model):
    gear_map = models.ForeignKey(GearMap, related_name='gear_map_data')
    target_name = models.CharField('target name', max_length=300)
    source_value = models.CharField('source value', max_length=300)

    def __str__(self):
        return '%s: %s' % (self.target_name, self.source_value)


class DBLogEntry(models.Model):
    time = models.DateTimeField(auto_now_add=True)
    level = models.CharField(max_length=10)
    message = models.TextField()

    class Meta:
        abstract = True


class ControllerLog(DBLogEntry):
    STATUS = (('f', 'Failed'), ('s', 'Successful'))
    module = models.CharField(max_length=30, blank=True, default='')
    process = models.CharField(max_length=20, blank=True, default='')
    status = models.CharField(max_length=2, blank=False, choices=STATUS, default='f')
    controller = models.CharField(max_length=20, blank=True, default='')


admin.site.register(Connector)
admin.site.register(Action)
admin.site.register(ActionSpecification)
admin.site.register(Connection)
admin.site.register(Gear)
admin.site.register(Plug)
admin.site.register(PlugSpecification)
