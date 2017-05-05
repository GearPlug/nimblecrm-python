from enum import Enum
from django.apps import apps
from apps.gp.controllers.database import MySQLController, PostgreSQLController, MSSQLController
from apps.gp.controllers.lead import GoogleFormsController, FacebookController
from apps.gp.controllers.crm import SugarCRMController
from apps.gp.controllers.email_marketing import MailChimpController, GetResponseController
from apps.gp.controllers.directory import GoogleContactsController
from apps.gp.controllers.ofimatic import GoogleSpreadSheetsController
from apps.gp.controllers.im import SlackController
from apps.gp.controllers.social import TwitterController
from apps.gp.controllers.project_management import JiraController
from apps.gp.controllers.repository import BitbucketController

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
        if connector == ConnectorEnum.Facebook:
            return FacebookController
        elif connector == ConnectorEnum.MySQL:
            return MySQLController
        elif connector == ConnectorEnum.SugarCRM:
            return SugarCRMController
        elif connector == ConnectorEnum.MailChimp:
            return MailChimpController
        elif connector == ConnectorEnum.GoogleSpreadSheets:
            return GoogleSpreadSheetsController
        elif connector == ConnectorEnum.PostgreSQL:
            return PostgreSQLController
        elif connector == ConnectorEnum.MSSQL:
            return MSSQLController
        elif connector == ConnectorEnum.JIRA:
            return JiraController
        elif connector == ConnectorEnum.Slack:
            return SlackController
        elif connector == ConnectorEnum.Bitbucket:
            return BitbucketController
        elif connector == ConnectorEnum.GoogleForms:
            return GoogleFormsController
        elif connector == ConnectorEnum.GoogleContacts:
            return GoogleContactsController
        elif connector == ConnectorEnum.GetResponse:
            return GetResponseController
        elif connector == ConnectorEnum.Twitter:
            return TwitterController
        return None