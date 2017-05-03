from enum import Enum
from django.apps import apps
from apps.gp.controllers import FacebookController, MySQLController, SugarCRMController, MailChimpController, \
    GoogleSpreadSheetsController, PostgreSQLController, MSSQLController, SlackController, BitbucketController, \
    JiraController, GoogleFormsController, GoogleContactsController, GetResponseController, TwitterController


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
    GoogleContacts = 12
    GetResponse = 13
    Twitter = 14

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


class MapField(object):
    """
    name = None
    label = None
    field_type = None
    options = None -> choices = None
    default = None
    required = False
    max_length = None
    """

    def __init__(self, d, controller=None, **kwargs):
        if controller == ConnectorEnum.SugarCRM:
            if 'name' in d:
                self.name = d['name']
            if 'label' in d:
                self.label = d['label']
            if 'options' in d:
                if isinstance(d['options'], dict):
                    self.choices = [(d['options'][choice]['name'], d['options'][choice]['value'])
                                    for choice in d['options']]
                    self.choices.insert(0, ('', ''))
            if 'type' in d:
                self.field_type = d['type']
            if 'len' in d:
                try:
                    self.max_length = int(d['len'])
                except:
                    self.max_length = 200
                    # print('field %s' % self.attrs)
        elif controller == ConnectorEnum.MailChimp:
            if 'tag' in d:
                self.name = d['tag']
            if 'name' in d:
                self.label = d['name']
            if 'required' in d:
                self.required = d['required']
            if 'default_value' in d and d['default_value'] != '':
                self.default = d['default_value']
            if 'type' in d:
                self.field_type = d['type']
            if 'options' in d:
                if 'size' in d['options']:
                    try:
                        self.max_length = int(d['options']['size'])
                    except:
                        pass
        elif controller == ConnectorEnum.Bitbucket:
            if 'name' in d:
                self.name = d['name']
                self.label = d['name']
            if 'required' in d:
                self.required = d['required']
            if 'type' in d:
                self.field_type = d['type']
            if 'values' in d:
                self.choices = [(choice, choice) for choice in d['values']]
                self.choices.insert(0, ('', ''))
        elif controller == ConnectorEnum.JIRA:
            # print(d)
            if 'id' in d:
                self.name = d['id']
            if 'name' in d:
                self.label = d['name']
            if 'required' in d:
                self.required = d['required']
            if 'schema' in d and 'type' in d['schema']:
                # Jira devuelve como Type nombres de objetos: ej. User, Issue
                # self.field_type = d['schema']['type']
                self.field_type = 'text'
            if 'allowedValues' in d and d['allowedValues']:
                self.choices = [(choice['id'], '{} ({})'.format(choice['name'], choice['id'])) for choice in
                                d['allowedValues']]
                self.choices.insert(0, ('', ''))
                self.field_type = 'choices'
        elif controller == ConnectorEnum.GetResponse:
            if 'id' in d:
                self.name = d['id']
            else:
                self.name = d['name']
            if 'name' in d:
                self.label = d['name']
            if 'required' in d:
                self.required = d['required']
            if 'type' in d:
                self.field_type = d['type']
            if 'values' in d and d['values']:
                self.choices = [(choice, choice) for choice in d['values']]
                self.choices.insert(0, ('', ''))
                self.field_type = 'choices'
        else:
            if 'name' in d:
                self.name = d['name']
            if 'label' in d:
                self.label = d['label']
            if 'default' in d or 'default_value' in d:
                self.default = d['default'] if 'default' in d else d['default_value']
            if 'options' in d:
                if isinstance(d['options'], dict):
                    self.choices = [(d['options'][choice]['name'], d['options'][choice]['value'])
                                    for choice in d['options']]
                    self.choices.insert(0, ('', ''))
            self.required = False

    @property
    def attrs(self):
        return [key for key, value in self.__dict__.items()]
