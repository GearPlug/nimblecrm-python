from enum import Enum
from django.apps import apps
from apps.gp.controllers.utils import dynamic_import


class ConnectorEnum(Enum):
    FacebookLeads = 1, 'lead', True
    MySQL = 2, 'database', False
    SugarCRM = 3, 'crm', False
    MailChimp = 4, 'email_marketing', False
    GoogleSpreadSheets = 5, 'ofimatic', True
    PostgreSQL = 6, 'database', False
    MSSQL = 7, 'database', False
    Slack = 8, 'im', True
    JIRA = 9, 'project_management', False
    Bitbucket = 10, 'repository', False
    GoogleForms = 11, 'lead', True
    Twitter = 12, 'social', True
    GetResponse = 13, 'email_marketing'
    GoogleContacts = 14, 'directory', True
    SurveyMonkey = 15, 'lead', True
    GoogleCalendar = 16, 'ofimatic', True
    MercadoLibre = 17, 'ecomerce'
    AmazonSellerCentral = 18, 'ecomerce'
    PayU = 19, 'ecomerce'
    Gmail = 20, 'email', True
    Ebay = 21, 'ecomerce'
    WooComerce = 22, 'ecomerce'
    Instagram = 23, 'social', True
    YouTube = 24, 'social', True
    Vimeo = 25, 'social'
    ZohoCRM = 26, 'crm'
    WunderList = 27, 'ofimatic', True
    SMS = 28, 'im'
    SMTP = 29, 'email'
    Evernote = 30, 'ofimatic', True
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
    Dropbox = 41, '', True
    Magento = 42, 'ecomerce'
    Asana = 43, 'project_management', True
    Mandrill = 44, 'email_marketing'

    def __new__(cls, *args, **kwargs):
        obj = object.__new__(cls)
        obj._value_ = args[0]
        obj.category = args[1]
        try:
            obj.has_auth = args[2]
        except:
            obj.has_auth = False
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


class GoogleAPIEnum(Enum):
    GoogleSpreadSheets = 1, 'https://www.googleapis.com/auth/drive'
    GoogleForms = 2, 'https://www.googleapis.com/auth/drive'
    GoogleCalendar = 3, 'https://www.googleapis.com/auth/calendar'
    Youtube = 4, 'https://www.googleapis.com/auth/youtube.readonly https://www.googleapis.com/auth/youtube.upload'
    GoogleContacts = 5, 'https://www.google.com/m8/feeds/'

    def __new__(cls, *args, **kwargs):
        obj = object.__new__(cls)
        obj._value_ = args[0]
        obj.scope = args[1]
        return obj

    def get_api(name=None):
        for field in GoogleAPIEnum:
            if name.lower() == field.name.lower():
                return field