from enum import Enum
from django.apps import apps
from apps.gp.controllers.database import MySQLController, PostgreSQLController, MSSQLController
from apps.gp.controllers.lead import GoogleFormsController, FacebookController, SurveyMonkeyController
from apps.gp.controllers.crm import SugarCRMController
from apps.gp.controllers.email_marketing import MailChimpController, GetResponseController
from apps.gp.controllers.directory import GoogleContactsController
from apps.gp.controllers.ofimatic import GoogleSpreadSheetsController,GoogleCalendarController
from apps.gp.controllers.im import SlackController
from apps.gp.controllers.social import TwitterController
from apps.gp.controllers.project_management import JiraController
from apps.gp.controllers.repository import BitbucketController
from apps.gp.controllers.utils import dynamic_import


class ConnectorEnum(Enum):
    Facebook = 1
    MySQL = 2
    SugarCRM = 3
    MailChimp = 4
    GoogleSpreadSheets = 5
    PostgreSQL = 6
    MSSQL = 7
    Slack = 8
    JIRA = 9
    Bitbucket = 10
    GoogleForms = 11
    Twitter = 12
    GetResponse = 13
    GoogleContacts = 14
    SurveyMonkey = 15
    GoogleCalendar = 16
    MercadoLibre = 17
    AmazonSellerCentral = 18
    PayU = 19
    Gmail = 20
    Ebay = 21
    WooComerce = 22
    Instagram = 23
    YouTube = 24

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
        dynamic_import(connector.name, path="apps.gp.enum", suffix='Controller')
        return None
