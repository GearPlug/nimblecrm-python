from enum import Enum
from django.apps import apps
from apps.gp.controllers.utils import dynamic_import


class ConnectorEnum(Enum):
    Facebook = 1, 'lead'
    MySQL = 2, 'database'
    SugarCRM = 3, 'crm'
    MailChimp = 4, 'email_marketing'
    GoogleSpreadSheets = 5, 'ofimatic'
    PostgreSQL = 6, 'database'
    MSSQL = 7, 'database'
    Slack = 8, 'im'
    JIRA = 9, 'project_management'
    Bitbucket = 10, 'repository'
    GoogleForms = 11, 'lead'
    Twitter = 12, 'social'
    GetResponse = 13, 'email_marketing'
    GoogleContacts = 14, 'directory'
    SurveyMonkey = 15, 'lead'
    GoogleCalendar = 16, 'ofimatic'
    MercadoLibre = 17, 'ecomerce'
    AmazonSellerCentral = 18, 'ecomerce'
    PayU = 19, 'ecomerce'
    Gmail = 20, 'email'
    Ebay = 21, 'ecomerce'
    WooComerce = 22, 'ecomerce'
    Instagram = 23, 'social'
    YouTube = 24, 'social'
    Vimeo = 25, 'social'
    ZohoCRM = 26, 'crm'
    WunderList = 27, 'ofimatic'

    def __new__(cls, *args, **kwargs):
        obj = object.__new__(cls)
        obj._value_ = args[0]
        obj.category = args[1]
        return obj

    def get_connector_data(connector):
        connector = ConnectorEnum.get_connector(connector)
        return ConnectorEnum.get_model(connector), ConnectorEnum.get_fields(connector)

    def get_connector(connector_id):
        connector_id = int(connector_id)
        for field in ConnectorEnum:
            if connector_id == int(field.value):
                return field

    def get_connector_list():
        return [field for field in ConnectorEnum]

    def get_fields(connector):
        model = apps.get_model('gp', '%sConnection' % connector.name)
        return [f.name for f in model._meta.get_fields() if
                f.name != 'id' and f.name != 'connection' and f.name != 'module']

    def get_model(connector):
        return apps.get_model('gp', '%sConnection' % connector.name)

    def get_controller(connector):
        return dynamic_import(connector.name, path="apps.gp.controllers.{0}".format(connector.category),
                              suffix='Controller')


class GoogleAPI(Enum):
    SpreadSheets = 1
    Forms = 2
    Calendar = 3
