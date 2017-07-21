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
    SMS = 28, 'im'
    SMTP = 29, 'email'
    Evernote = 30, 'ofimatic'
    Salesforce = 31, 'crm'
    Vtiger = 32, 'crm'
    ProsperWorks = 33, 'crm'
    HubSpot = 34, 'crm'
    PipeDrive = 35, 'crm'
    DynamicCRM = 36, 'crm'
    FreshDesk = 37, 'crm'
    AgileCRM = 38, 'crm'
    GitLab = 39, 'repository'
    Shopify = 40, 'ecomerce'
    Dropbox = 41, ''

    def __new__(cls, *args, **kwargs):
        obj = object.__new__(cls)
        obj._value_ = args[0]
        obj.category = args[1]
        return obj

    def get_connector_data(connector):
        return ConnectorEnum.get_model(connector), ConnectorEnum.get_fields(connector)

    def get_connector(connector_id=None, name=None):
        if connector_id is not None:
            if isinstance(connector_id, ConnectorEnum):
                connector_id = connector_id.value
            connector_id = int(connector_id)
            for field in ConnectorEnum:
                if connector_id == int(field.value):
                    return field
        elif name is not None and isinstance(name, str):
            for field in ConnectorEnum:
                if name.lower() == field.name.lower():
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
    SpreadSheets = 1, 'https://www.googleapis.com/auth/drive'
    Forms = 2, 'https://www.googleapis.com/auth/drive'
    Calendar = 3, 'https://www.googleapis.com/auth/calendar'
    YouTube = 4, 'https://www.googleapis.com/auth/youtube.readonly https://www.googleapis.com/auth/youtube.upload'
    Contacts = 5, 'https://www.google.com/m8/feeds/'

    def __new__(cls, *args, **kwargs):
        obj = object.__new__(cls)
        obj._value_ = args[0]
        obj.scope = args[1]
        return obj
