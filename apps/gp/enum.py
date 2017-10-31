from enum import Enum
from django.apps import apps
from apps.gp.controllers.utils import dynamic_import


class ConnectorEnum(Enum):
    """
    FORMATO:
    Name = ID (igual al de db), category, connection_type

    """
    FacebookLeads = 1, 'lead', 'special'
    MySQL = 2, 'database', 'form'
    SugarCRM = 3, 'crm', 'form'
    MailChimp = 4, 'email_marketing', 'authorization'
    GoogleSpreadSheets = 5, 'ofimatic', 'authorization'
    PostgreSQL = 6, 'database', 'form'
    MSSQL = 7, 'database', 'form'
    Slack = 8, 'im', 'authorization'
    JIRA = 9, 'project_management', 'form'
    Bitbucket = 10, 'repository', 'form'
    GoogleForms = 11, 'lead', 'authorization'
    Twitter = 12, 'social', 'authorization'
    GetResponse = 13, 'email_marketing'
    GoogleContacts = 14, 'directory', 'authorization'
    SurveyMonkey = 15, 'lead', 'authorization'
    GoogleCalendar = 16, 'ofimatic', 'authorization'
    MercadoLibre = 17, 'ecomerce', 'special'
    AmazonSellerCentral = 18, 'ecomerce'
    PayU = 19, 'ecomerce'
    Gmail = 20, 'email', 'authorization'
    Ebay = 21, 'ecomerce'
    WooComerce = 22, 'ecomerce'
    Instagram = 23, 'social', 'authorization'
    YouTube = 24, 'social', 'authorization'
    Vimeo = 25, 'social'
    ZohoCRM = 26, 'crm'
    WunderList = 27, 'ofimatic', 'authorization'
    SMS = 28, 'im', None
    SMTP = 29, 'email', None
    Evernote = 30, 'ofimatic', 'authorization'
    Salesforce = 31, 'crm'
    Vtiger = 32, 'crm'
    ProsperWorks = 33, 'crm'
    HubSpot = 34, 'crm'
    PipeDrive = 35, 'crm'
    DynamicCRM = 36, 'crm'
    FreshDesk = 37, 'crm'
    AgileCRM = 38, 'crm'
    GitLab = 39, 'repository', 'authorization'
    Shopify = 40, 'ecomerce', 'special'
    Dropbox = 41, '', 'authorization'
    Magento = 42, 'ecomerce'
    Asana = 43, 'project_management', 'authorization'
    Mandrill = 44, 'email_marketing'
    ActiveCampaign = 45, 'crm', 'form'
    TypeForm = 46, 'lead', 'form'
    InfusionSoft = 47, 'crm', 'authorization'
    Batchbook = 49, 'crm', 'form'

    def __new__(cls, *args, **kwargs):
        obj = object.__new__(cls)
        obj._value_ = args[0]
        obj.category = args[1]
        try:
            obj.connection_type = args[2]
        except:
            obj.connection_type = 'form'
        return obj

    def get_connector_data(connector):
        return ConnectorEnum.get_model(connector), ConnectorEnum.get_fields(
            connector)

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

    def get_connector_list(is_active=None, webhook=None):
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
    "NAME = ID?, SCOPE"
    GoogleSpreadSheets = 1, 'https://www.googleapis.com/auth/drive'
    GoogleForms = 2, 'https://www.googleapis.com/auth/drive'
    GoogleCalendar = 3, 'https://www.googleapis.com/auth/calendar'
    Youtube = 4, 'https://www.googleapis.com/auth/youtube.readonly https://www.googleapis.com/auth/youtube.upload'
    GoogleContacts = 5, 'https://www.google.com/m8/feeds/'
    Gmail = 6, 'https://www.googleapis.com/auth/gmail.modify https://www.googleapis.com/auth/pubsub'

    def __new__(cls, *args, **kwargs):
        obj = object.__new__(cls)
        obj._value_ = args[0]
        obj.scope = args[1]
        return obj

    def get_api(name=None):
        for field in GoogleAPIEnum:
            if name.lower() == field.name.lower():
                return field
