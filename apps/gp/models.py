from django.db import models
from django.contrib import admin
from apps.user.models import User

connections = ['connection_facebook', 'connection_mysql']


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
        return self.name


class FacebookConnection(models.Model):
    connection = models.OneToOneField(Connection, on_delete=models.CASCADE, related_name='connection_facebook')
    name = models.CharField('name', max_length=120)
    id_page = models.CharField('id page', max_length=300)
    id_form = models.CharField('id form', max_length=300)
    token = models.CharField('token', max_length=300)

    def __str__(self):
        return self.name


class MySQLConnection(models.Model):
    connection = models.OneToOneField(Connection, on_delete=models.CASCADE, related_name='connection_mysql')
    name = models.CharField('name', max_length=120)
    host = models.CharField('host', max_length=40)
    database = models.CharField('database', max_length=40)
    port = models.CharField('port', max_length=5)
    connection_user = models.CharField('user', max_length=40)
    connection_password = models.CharField('password', max_length=40)

    def __str__(self):
        return self.name


class Plug(models.Model):
    name = models.CharField('name', max_length=120)
    connection = models.ForeignKey(Connection, null=True, on_delete=models.CASCADE)
    action = models.ForeignKey(Action, null=True, on_delete=models.CASCADE)
    user = models.ForeignKey(User)

    def __str__(self):
        return self.name


class PlugSpecification(models.Model):
    plug = models.ForeignKey(Plug, on_delete=models.CASCADE, related_name='plug_specification')
    action_specification = models.ForeignKey(ActionSpecification)
    value = models.CharField('value', max_length=1000)

    class Meta:
        unique_together = ['plug', 'action_specification']


class Gear(models.Model):
    name = models.CharField('name', max_length=120)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    source = models.ForeignKey(Plug, null=True, on_delete=models.CASCADE, related_name='source_plug')
    target = models.ForeignKey(Plug, null=True, on_delete=models.CASCADE, related_name='target_plug')


class StoredData(models.Model):
    plug = models.ForeignKey(Plug, related_name='pulled_data', )
    name = models.CharField('name', max_length=300)
    value = models.CharField('value', max_length=3000)
    datetime = models.DateTimeField(auto_now_add=True)
    object_id = models.CharField('object_id', max_length=50, null=False)

    class Meta:
        unique_together = ['plug', 'object_id', 'name']

    def __str__(self):
        return '%s %s %s' % (self.id, self.name, self.object_id)


admin.site.register(Connector)
admin.site.register(Action)
admin.site.register(ActionSpecification)
admin.site.register(Connection)
admin.site.register(FacebookConnection)
admin.site.register(Gear)
admin.site.register(Plug)
admin.site.register(PlugSpecification)
