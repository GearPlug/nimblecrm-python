from django.contrib import admin
from django.contrib.auth.models import User
from apps.gp.enum import ConnectorEnum, FilterEnum
from django.db import models
from apps.gp.model_fields import JSONField

connections = ['connection_{0}'.format(connector.name.lower()) for connector in ConnectorEnum.get_connector_list()]


class Category(models.Model):
    name = models.CharField('name', max_length=100)


class Connector(models.Model):
    name = models.CharField('name', max_length=120)
    short_description = models.TextField('short description', max_length=256, default='')
    description = models.TextField('description', max_length=5000, default='')
    is_active = models.BooleanField('is active', default=False)
    is_source = models.BooleanField('is source', default=False)
    is_target = models.BooleanField('is target', default=False)
    icon15 = models.ImageField('icon 15px', upload_to='connector/icon', null=True, default=None)
    icon73 = models.ImageField('icon 73px', upload_to='connector/icon', null=True, default=None)
    icon110 = models.ImageField('icon 110px', upload_to='connector/icon', null=True, default=None)
    category = models.ManyToManyField(Category, through='ConnectorCategory')
    connection_help_text = models.CharField('connection help text', max_length=3000, default='')

    class Meta:
        verbose_name = 'connector'

    def __str__(self):
        return self.name


class ConnectorCategory(models.Model):
    connector = models.ForeignKey(Connector)
    category = models.ForeignKey(Category)

    class Meta:
        db_table = 'gp_connector__category'


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
        return self.name + ' on ' + self.connector.name


class ActionSpecification(models.Model):
    action = models.ForeignKey(Action, on_delete=models.CASCADE, related_name='action_specification')
    name = models.CharField('name', max_length=30)

    def __str__(self):
        return self.action.name + ': ' + self.name + ' on ' + self.action.connector.name


class Connection(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    connector = models.ForeignKey(Connector, default=2, on_delete=models.CASCADE)
    created = models.DateTimeField('created', auto_now_add=True)
    last_update = models.DateTimeField('last update', auto_now=True)
    is_deleted = models.BooleanField('is deleted', default=False)
    is_active = models.BooleanField('is active', default=True)

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


class JiraConnection(models.Model):
    connection = models.OneToOneField(Connection, on_delete=models.CASCADE, related_name='connection_jira')
    name = models.CharField('name', max_length=200)
    host = models.CharField('host', max_length=200)
    connection_user = models.CharField('user', max_length=60)
    connection_password = models.CharField('password', max_length=40)

    def __str__(self):
        return self.name


class FacebookLeadsConnection(models.Model):
    connection = models.OneToOneField(Connection, on_delete=models.CASCADE, related_name='connection_facebookleads')
    name = models.CharField('name', max_length=200)
    token = models.CharField('token', max_length=300)

    def __str__(self):
        return self.name


class InstagramConnection(models.Model):
    connection = models.OneToOneField(Connection, on_delete=models.CASCADE, related_name='connection_instagram')
    name = models.CharField('name', max_length=200)
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
        return '{0}'.format(self.name)


class PostgreSQLConnection(models.Model):
    connection = models.OneToOneField(Connection, on_delete=models.CASCADE, related_name='connection_postgresql')
    name = models.CharField('name', max_length=200)
    host = models.CharField('host', max_length=200)
    database = models.CharField('database', max_length=200)
    schema = models.CharField('schema', max_length=200)
    table = models.CharField('table', max_length=200)
    port = models.CharField('port', max_length=7)
    connection_user = models.CharField('user', max_length=60)
    connection_password = models.CharField('password', max_length=40)

    def __str__(self):
        return self.name


class MSSQLConnection(models.Model):
    connection = models.OneToOneField(Connection, on_delete=models.CASCADE, related_name='connection_mssql')
    name = models.CharField('name', max_length=200)
    host = models.CharField('host', max_length=200)
    database = models.CharField('database', max_length=200)
    table = models.CharField('table', max_length=200)
    port = models.CharField('port', max_length=7)
    connection_user = models.CharField('user', max_length=60)
    connection_password = models.CharField('password', max_length=40)

    def __str__(self):
        return self.name


class MagentoConnection(models.Model):
    connection = models.OneToOneField(Connection, on_delete=models.CASCADE, related_name='connection_magento')
    name = models.CharField('name', max_length=200)
    host = models.CharField('host', max_length=200)
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
    token = models.CharField('user', max_length=200)

    def __str__(self):
        return self.name


class MandrillConnection(models.Model):
    connection = models.OneToOneField(Connection, on_delete=models.CASCADE, related_name='connection_mandrill')
    name = models.CharField('name', max_length=200)
    api_key = models.CharField('api key', max_length=200)

    def __str__(self):
        return self.name


class GetResponseConnection(models.Model):
    connection = models.OneToOneField(Connection, on_delete=models.CASCADE, related_name='connection_getresponse')
    name = models.CharField('name', max_length=200)
    api_key = models.CharField('api key', max_length=200)


class SurveyMonkeyConnection(models.Model):
    connection = models.OneToOneField(Connection, on_delete=models.CASCADE, related_name='connection_surveymonkey')
    name = models.CharField('name', max_length=200)
    token = models.CharField('token', max_length=300)

    def __str__(self):
        return self.name


class ShopifyConnection(models.Model):
    connection = models.OneToOneField(Connection, on_delete=models.CASCADE, related_name='connection_shopify')
    name = models.CharField('name', max_length=200)
    token = models.CharField('token', max_length=300)
    shop_url = models.CharField('shop_url', max_length=300)

    def __str__(self):
        return self.name


class TwitterConnection(models.Model):
    connection = models.OneToOneField(Connection, on_delete=models.CASCADE, related_name='connection_twitter')
    name = models.CharField('name', max_length=200)
    token = models.CharField('token', max_length=300)
    token_secret = models.CharField('token', max_length=300)

    def __str__(self):
        return self.name


class GoogleSpreadSheetsConnection(models.Model):
    connection = models.OneToOneField(Connection, on_delete=models.CASCADE,
                                      related_name='connection_googlespreadsheets')
    name = models.CharField('name', max_length=200)
    credentials_json = JSONField(blank=True, null=True)

    def __str__(self):
        return self.name


class GoogleFormsConnection(models.Model):
    connection = models.OneToOneField(Connection, on_delete=models.CASCADE, related_name='connection_googleforms')
    name = models.CharField('name', max_length=200)
    credentials_json = JSONField(blank=True, null=True)

    def __str__(self):
        return self.name


class GoogleCalendarConnection(models.Model):
    connection = models.OneToOneField(Connection, on_delete=models.CASCADE, related_name='connection_googlecalendar')
    name = models.CharField('name', max_length=200)
    credentials_json = JSONField(blank=True, null=True)

    def __str__(self):
        return self.name


class YouTubeConnection(models.Model):
    connection = models.OneToOneField(Connection, on_delete=models.CASCADE, related_name='connection_youtube')
    name = models.CharField('name', max_length=200)
    credentials_json = JSONField(blank=True, null=True)

    def __str__(self):
        return self.name


class SlackConnection(models.Model):
    connection = models.OneToOneField(Connection, on_delete=models.CASCADE, related_name='connection_slack')
    name = models.CharField('name', max_length=200)
    token = models.CharField('token', max_length=100)

    def __str__(self):
        return self.name


class EvernoteConnection(models.Model):
    connection = models.OneToOneField(Connection, on_delete=models.CASCADE, related_name='connection_evernote')
    name = models.CharField('name', max_length=200)
    token = models.CharField('token', max_length=100)

    def __str__(self):
        return self.name


class BitbucketConnection(models.Model):
    connection = models.OneToOneField(Connection, on_delete=models.CASCADE, related_name='connection_bitbucket')
    name = models.CharField('name', max_length=200)
    connection_user = models.CharField('user', max_length=60)
    connection_password = models.CharField('password', max_length=40)

    def __str__(self):
        return self.name


class GoogleContactsConnection(models.Model):
    connection = models.OneToOneField(Connection, on_delete=models.CASCADE, related_name='connection_googlecontacts')
    name = models.CharField('name', max_length=200)
    credentials_json = JSONField(blank=True, null=True)

    def __str__(self):
        return self.name


class WunderListConnection(models.Model):
    connection = models.OneToOneField(Connection, on_delete=models.CASCADE, related_name='connection_wunderlist')
    name = models.CharField('name', max_length=200)
    token = models.CharField('token', max_length=300)

    def __str__(self):
        return self.name


class ZohoCRMConnection(models.Model):
    connection = models.OneToOneField(Connection, on_delete=models.CASCADE, related_name='connection_zohocrm')
    token = models.CharField('token', max_length=300)
    name = models.CharField('name', max_length=200)

    def __str__(self):
        return self.name


class HubSpotConnection(models.Model):
    connection = models.OneToOneField(Connection, on_delete=models.CASCADE, related_name='connection_hubspotcrm')
    name = models.CharField('name', max_length=200)
    token = models.CharField('token', max_length=300)
    refresh_token = models.CharField('token', max_length=300)

    def __str__(self):
        return self.name


class SMSConnection(models.Model):
    connection = models.OneToOneField(Connection, on_delete=models.CASCADE, related_name='connection_sms')
    name = models.CharField('name', max_length=200)
    connection_user = models.CharField('user', max_length=60)
    connection_password = models.CharField('password', max_length=40)

    def __str__(self):
        return self.name


class SalesforceConnection(models.Model):
    connection = models.OneToOneField(Connection, on_delete=models.CASCADE, related_name='connection_salesforce')
    name = models.CharField('name', max_length=200)
    token = models.CharField('token', max_length=300)

    def __str__(self):
        return self.name


class SMTPConnection(models.Model):
    connection = models.OneToOneField(Connection, on_delete=models.CASCADE, related_name='connection_smtp')
    name = models.CharField('name', max_length=200)
    host = models.CharField('host', max_length=200)
    port = models.CharField('port', max_length=200)
    connection_user = models.CharField('user', max_length=60)
    connection_password = models.CharField('password', max_length=40)

    def __str__(self):
        return self.name


class WebhookConnection(models.Model):
    connection = models.OneToOneField(Connection, on_delete=models.CASCADE, related_name='connection_webhook')
    name = models.CharField('name', max_length=200)


class AsanaConnection(models.Model):
    connection = models.OneToOneField(Connection, on_delete=models.CASCADE, related_name='connection_asana')
    name = models.CharField('name', max_length=200)
    token = models.CharField('token', max_length=300)
    refresh_token = models.CharField('refresh token', max_length=300)
    token_expiration_timestamp = models.CharField('token expiration timestamp', max_length=300)

    def __str__(self):
        return self.name


class VtigerConnection(models.Model):
    connection = models.OneToOneField(Connection, on_delete=models.CASCADE, related_name='connection_vtiger')
    name = models.CharField('name', max_length=200)
    connection_user = models.CharField('user', max_length=60)
    connection_access_key = models.CharField('access key', max_length=100, blank=True, null=True)
    url = models.URLField('url')

    def __str__(self):
        return self.name


class MercadoLibreConnection(models.Model):
    SITES = (('MLA', 'Argentina'), ('MLB', 'Brazil'), ('MCO', 'Colombia'),
             ('MCR', 'Costa Rica'), ('MEC', 'Ecuador'),
             ('MLC', 'Chile'), ('MLM', 'Mexico'), ('MLU', 'Uruguay'),
             ('MLV', 'Venezuela'), ('MPA', 'Panama'),
             ('MPE', 'Peru'), ('MPT', 'Portugal'),
             ('MRD', 'Republica Dominicana'))
    connection = models.OneToOneField(Connection, on_delete=models.CASCADE, related_name='connection_mercadolibre')
    name = models.CharField('name', max_length=200)
    user_id = models.CharField('user_id', max_length=200)
    token = models.CharField('token', max_length=300)
    site = models.CharField(max_length=3, choices=SITES)

    def __str__(self):
        return self.name


class GmailConnection(models.Model):
    connection = models.OneToOneField(Connection, on_delete=models.CASCADE,
                                      related_name='connection_gmail')
    name = models.CharField('name', max_length=200)
    credentials_json = JSONField(blank=True, null=True)

    def __str__(self):
        return self.name


class GitLabConnection(models.Model):
    connection = models.OneToOneField(Connection, on_delete=models.CASCADE, related_name='connection_gitlab')
    name = models.CharField('name', max_length=200)
    token = models.CharField('token', max_length=300)
    refresh_token = models.CharField('refresh token', max_length=300)

    def __str__(self):
        return self.name


class InfusionSoftConnection(models.Model):
    connection = models.OneToOneField(Connection, on_delete=models.CASCADE, related_name='connection_infusionsoft')
    name = models.CharField('name', max_length=200)
    token = models.CharField('token', max_length=300)
    refresh_token = models.CharField('refresh token', max_length=300)
    token_expiration_time = models.CharField('token expiration time', max_length=300)

    def __str__(self):
        return self.name


class ActiveCampaignConnection(models.Model):
    connection = models.OneToOneField(Connection, on_delete=models.CASCADE, related_name='connection_activecampaign')
    name = models.CharField('name', max_length=200)
    host = models.CharField('host', max_length=200)
    connection_access_key = models.CharField('access key', max_length=100)

    def __str__(self):
        return self.name


class BatchbookConnection(models.Model):
    connection = models.OneToOneField(Connection, on_delete=models.CASCADE, related_name='connection_batchbook')
    name = models.CharField('name', max_length=200)
    account_name = models.CharField('account_name', max_length=200)
    access_key = models.CharField('access key', max_length=100)

    def __str__(self):
        return self.name


class TypeFormConnection(models.Model):
    connection = models.OneToOneField(Connection, on_delete=models.CASCADE, related_name='connection_typeform')
    name = models.CharField('name', max_length=200)
    token = models.CharField('token', max_length=400)

    def __str__(self):
        return self.name


class OdooCRMConnection(models.Model):
    connection = models.OneToOneField(Connection, on_delete=models.CASCADE, related_name='connection_odoocrm')
    name = models.CharField('name', max_length=200)
    url = models.CharField('url', max_length=200)
    database = models.CharField('database', max_length=200)
    connection_user = models.CharField('user', max_length=200)
    connection_password = models.CharField('password', max_length=200)

    def __str__(self):
        return self.name


class ActEssentialsConnection(models.Model):
    connection = models.OneToOneField(Connection, on_delete=models.CASCADE, related_name='connection_actessentials')
    name = models.CharField('name', max_length=200)
    api_key = models.CharField('API Key', max_length=400)

    def __str__(self):
        return self.name


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
    is_tested = models.BooleanField(default=False)

    @property
    def is_source(self):
        return self.plug_type == 'source'

    @property
    def is_target(self):
        return self.plug_type == 'target'

    def __str__(self):
        return self.name


class PlugActionSpecification(models.Model):
    plug = models.ForeignKey(Plug, on_delete=models.CASCADE, related_name='plug_action_specification', )
    action_specification = models.ForeignKey(ActionSpecification, on_delete=models.CASCADE,
                                             related_name='action_specification')
    value = models.CharField('value', max_length=1000)

    class Meta:
        unique_together = ['plug', 'action_specification']


class StoredData(models.Model):
    plug = models.ForeignKey(Plug, related_name='stored_data')
    connection = models.ForeignKey(Connection, related_name='stored_data')
    name = models.CharField('name', max_length=300)
    value = models.CharField('value', max_length=3000, default='', blank=True)
    datetime = models.DateTimeField(auto_now_add=True)
    object_id = models.CharField('object_id', max_length=150, null=True)

    def __str__(self):
        return '{0} {1}'.format(self.name, self.object_id)


class GearGroup(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField('name', max_length=64)

    def __str__(self):
        return self.name


class Gear(models.Model):
    name = models.CharField('name', max_length=120)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    source = models.ForeignKey(Plug, null=True, on_delete=models.SET_NULL, related_name='gear_source')
    target = models.ForeignKey(Plug, null=True, on_delete=models.SET_NULL, related_name='gear_target')
    is_active = models.BooleanField('is active', default=False)
    created = models.DateTimeField('created', auto_now_add=True)
    last_update = models.DateTimeField('last update', auto_now=True)
    gear_group = models.ForeignKey(GearGroup, null=True, on_delete=models.SET_NULL, related_name='gear')

    @property
    def is_running(self):
        return self.is_active and self.gear_map.is_active


class GearFilter(models.Model):
    OPTIONS = tuple((field.value, field.name) for field in FilterEnum)
    gear = models.ForeignKey(Gear, related_name='gear_filter')
    field_name = models.CharField('field name', max_length=256)
    option = models.IntegerField('option', choices=OPTIONS)
    comparison_data = models.CharField('comparison data', max_length=100)
    is_active = models.BooleanField('is active', default=False)


class GearMap(models.Model):
    gear = models.OneToOneField(Gear, related_name='gear_map')
    created = models.DateTimeField('created', auto_now_add=True)
    last_update = models.DateTimeField('last update', auto_now=True)
    is_active = models.BooleanField('is active', default=True)
    last_sent_stored_data = models.ForeignKey(StoredData, related_name='gear_map', null=True, default=None,
                                              on_delete=models.SET_NULL)
    last_source_update = models.DateTimeField(null=True, default=None)
    last_source_order_by_field_value = models.CharField(max_length=64, null=True, blank=True, default=None)
    created = models.DateTimeField('created', auto_now_add=True)

    class Meta:
        unique_together = ['id', 'gear']


class GearMapData(models.Model):
    gear_map = models.ForeignKey(GearMap, related_name='gear_map_data')
    version = models.SmallIntegerField('version', default=1)
    target_name = models.CharField('target name', max_length=300)
    source_value = models.CharField('source value', max_length=300)

    def __str__(self):
        return '%s: %s' % (self.target_name, self.source_value)


class Webhook(models.Model):
    name = models.CharField('webhook name', max_length=100)
    plug = models.OneToOneField(Plug, on_delete=models.CASCADE, related_name='webhook')
    url = models.URLField('url')
    generated_id = models.CharField('generated id', max_length=200)
    created = models.DateTimeField('created', auto_now_add=True)
    is_active = models.BooleanField('is active', default=False)
    is_deleted = models.BooleanField('is deleted', default=False)
    expiration = models.CharField('expiration', max_length=200, null=True, default=None)

    def __str__(self):
        return '%s webhook of %s' % (self.name, self.plug)


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
admin.site.register(GearGroup)
admin.site.register(Plug)
admin.site.register(PlugActionSpecification)
