from apps.gp.controllers.base import BaseController
from apps.gp.controllers.exception import ControllerError
from apps.gp.controllers.utils import get_dict_with_source_data
from apps.gp.enum import ConnectorEnum
from apps.gp.models import StoredData, ActionSpecification
from apps.gp.map import MapField
from django.urls import reverse

from django.conf import settings
import requests
from base64 import b64encode
from jira import JIRA
import time


class JiraController(BaseController):
    _connection = None

    def __init__(self, *args, **kwargs):
        BaseController.__init__(self, *args, **kwargs)

    def create_connection(self, *args, **kwargs):
        if args:
            super(JiraController, self).create_connection(*args)
            if self._connection_object is not None:
                host = self._connection_object.host
                user = self._connection_object.connection_user
                password = self._connection_object.connection_password
        elif kwargs:
            host = kwargs.pop('host', None)
            user = kwargs.pop('connection_user', None)
            password = kwargs.pop('connection_password', None)
        else:
            host, user, password = None, None, None
        if host and user and password:
            try:
                self._connection = JIRA(host, basic_auth=(user, password))
            except Exception as e:
                print("Error getting the Jira attributes")
                print(e)
                self._connection = None
        return self._connection is not None

    def send_stored_data(self, source_data, target_fields, is_first=False):
        obj_list = []
        data_list = get_dict_with_source_data(source_data, target_fields)
        if is_first:
            if data_list:
                try:
                    data_list = [data_list[-1]]
                except:
                    data_list = []
        if self._plug is not None:
            for obj in data_list:
                res = self.create_issue(self._plug.plug_action_specification.all()[0].value, obj)
            extra = {'controller': 'jira'}
            return
        raise ControllerError("Incomplete.")

    def download_to_stored_data(self, connection_object=None, plug=None, issue=None, **kwargs):
        if issue is not None:
            issue_key = issue['key']
            _items = []
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug,
                                          object_id=issue_key)
            if not q.exists():
                for k, v in issue['fields'].items():
                    obj = StoredData(connection=connection_object.connection, plug=plug,
                                     object_id=issue_key, name=k, value=v or '')
                    _items.append(obj)
            extra = {}
            for item in _items:
                extra['status'] = 's'
                extra = {'controller': 'jira'}
                self._log.info('Item ID: %s, Connection: %s, Plug: %s successfully stored.' % (
                    item.object_id, item.plug.id, item.connection.id), extra=extra)
                item.save()
        return False

    def get_projects(self):
        return self._connection.projects()

    def create_issue(self, project_id, fields):
        if 'reporter' in fields:
            reporter_name = fields['reporter']
            fields['reporter'] = {'name': reporter_name}
        if 'assignee' in fields:
            assignee_name = fields['assignee']
            fields['assignee'] = {'name': assignee_name}
        if 'issuetype' in fields:
            issue_type = fields['issuetype']
            fields['issuetype'] = {'id': issue_type}
        if 'priority' in fields:
            priority = fields['priority']
            fields['priority'] = {'id': priority}
        fields['project'] = project_id
        return self._connection.create_issue(fields=fields)

    def create_webhook(self):
        url = '{}/rest/webhooks/1.0/webhook'.format(self._connection_object.host)
        key = self.get_key(self._plug.plug_action_specification.all()[0].value)
        body = {
            "name": "Gearplug Webhook",
            "url": "http://grplug.com/wizard/jira/webhook/event/",
            "events": [
                "jira:issue_created",
            ],
            "jqlFilter": "Project={}".format(key),
            "excludeIssueDetails": False
        }
        r = requests.post(url, headers=self._get_header(), json=body)
        if r.status_code == 201:
            return True
        return False

    def get_key(self, project_id):
        for project in self.get_projects():
            if project.id == project_id:
                return project.key
        return None

    def _get_header(self):
        authorization = '{}:{}'.format(self._connection_object.connection_user,
                                       self._connection_object.connection_password)
        return {'Accept': 'application/json',
                'Authorization': 'Basic {0}'.format(b64encode(authorization.encode('UTF-8')).decode('UTF-8'))}

    def get_users(self):
        payload = {
            'project': self.get_key(self._plug.plug_action_specification.all()[0].value)
        }

        url = 'http://jira.grplug.com:8080/rest/api/2/user/assignable/search'
        r = requests.get(url, headers=self._get_header(), params=payload)
        if r.status_code == requests.codes.ok:
            return [{'id': u['name'], 'name': u['displayName']} for u in r.json()]
        return []

    def get_meta(self):
        meta = self._connection.createmeta(projectIds=self._plug.plug_action_specification.all()[0].value,
                                           issuetypeNames='Task', expand='projects.issuetypes.fields')
        exclude = ['attachment', 'project']

        users = self.get_users()

        def f(d, v):
            d.update({'id': v})
            return d

        _dict = [f(v, k) for k, v in meta['projects'][0]['issuetypes'][0]['fields'].items() if
                 k not in exclude]

        for d in _dict:
            if d['id'] == 'reporter' or d['id'] == 'assignee':
                d['allowedValues'] = users

        return sorted(_dict, key=lambda i: i['name'])

    def get_target_fields(self, **kwargs):
        return self.get_meta(**kwargs)

    def get_mapping_fields(self, **kwargs):
        fields = self.jirac.get_meta()
        return [MapField(f, controller=ConnectorEnum.JIRA) for f in fields]

class AsanaController(BaseController):
    _token = None
    _refresh_token = None
    _token_expiration_timestamp = None
    __refresh_url = 'https://app.asana.com/-/oauth_token'

    def create_connection(self, *args, **kwargs):
        if args:
            super(AsanaController, self).create_connection(*args)
            if self._connection_object is not None:
                self._token = self._connection_object.token
                self._refresh_token = self._connection_object.refresh_token
                self._token_expiration_timestamp = self._connection_object.token_expiration_timestamp

    def test_connection(self):
        if self.is_token_expired():
            self.refresh_token()

        information = self.get_user_information()
        print(information)
        return information is not None

    def is_token_expired(self):
        print(float(self._token_expiration_timestamp), time.time(), float(self._token_expiration_timestamp) < time.time())
        return float(self._token_expiration_timestamp) < time.time()

    def refresh_token(self):
        try:
            # Data para la peticion de nuevo token
            data_refresh_token = [
                ('grant_type', 'refresh_token'),
                ('client_id', settings.ASANA_CLIENT_ID),
                ('client_secret', settings.ASANA_CLIENT_SECRET),
                ('refresh_token', self._refresh_token),
                ('redirect_uri', settings.ASANA_REDIRECT_URL),
            ]
            new_token = requests.post(self.__refresh_url, data=data_refresh_token).json()
            self._connection_object.token = new_token['access_token']
            self._connection_object.save()
            self._token = self._connection_object.token

        except Exception as e:
            new_token = None
        print(new_token)
        return new_token['access_token']

    def get_user_information(self):
        # Headers para Request de usuario principal
        if self.is_token_expired():
            self.refresh_token()
        headers_1 = {
            'Authorization': 'Bearer {0}'.format(self._token),
        }
        # Request para obtener datos de usuario creador de la tarea
        r = requests.get('https://app.asana.com/api/1.0/users/me',
                         headers=headers_1)
        try:
            response = r.json()
            print('user info')
            print(response)
            return response['data']
        except Exception as e:
            print(e)
        return None

    def get_workspaces(self):
        try:
            print('workspaces')
            return self.get_user_information()['workspaces']
        except Exception as e:
            print(e)
            return []

    def get_action_specification_options(self, action_specification_id):
        action_specification = ActionSpecification.objects.get(pk=action_specification_id)
        if action_specification.name.lower() == 'workspace':
            return tuple({'id': w['id'], 'name': w['name']} for w in self.get_workspaces())
        else:
            raise ControllerError("That specification doesn't belong to an action in this connector.")

    def create_webhook(self):
        if self.is_token_expired():
            self.refresh_token()
        action = self._plug.action.name
        if action == 'read created task':
            print('webhook if')
            workspace = self._plug.plug_action_specification.get(action_specification__name = 'workspace')
            print(workspace.value)
            headers = {
                'Authorization': 'Bearer {}'.format(self._token)
            }
            id_webhook = 2
            url_base = 'http://26677b10.ngrok.io'
            url_path = reverse('home:webhook', kwargs={'connector':'asana', 'webhook_id':id_webhook})
            print('url --> ', url_base+url_path)

            data = [
                ('resource', workspace.value),
                ('target', url_base+url_path),
            ]

            r = requests.post('https://app.asana.com/api/1.0/webhooks',
                              headers=headers,
                              data=data)
            print(r.json())
            # return r.json()
        raise Exception('feo')



        #
        # workspace = int(request.POST['workspaces'])
        #
        # # Headers del post para Asana server

        #
        # # Id del webhook a crear, control internet.
        # id_webhook = random.randint(1, 100)
        #
        # # data o payload contenida en el post a Asana server

        #
        # # request a Asana server

        # return render(request, 'create_webhook.html',
        #               {'created_webhook': r.json()})

    def download_to_stored_data(self, connection_object=None, plug=None, task=None, **kwargs):
        pass