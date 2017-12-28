from django.shortcuts import HttpResponse
from apps.gp.controllers.base import BaseController
from apps.gp.controllers.exception import ControllerError
from apps.gp.controllers.utils import get_dict_with_source_data
from apps.gp.enum import ConnectorEnum
from apps.gp.models import StoredData, ActionSpecification, Webhook, Plug
from apps.gp.map import MapField
from django.urls import reverse
from django.db.models import Q
from django.conf import settings
import requests
from base64 import b64encode
from jira.client import Client as JIRAClient
import time
import datetime
import json


class JIRAController(BaseController):
    _connection = None

    def __init__(self, connection=None, plug=None):
        BaseController.__init__(self, connection=connection, plug=plug)

    def create_connection(self, connection=None, plug=None):
        super(JIRAController, self).create_connection(connection=connection, plug=plug)
        if self._connection_object is not None:
            try:
                host = self._connection_object.host
                user = self._connection_object.connection_user
                password = self._connection_object.connection_password
            except AttributeError as e:
                raise ControllerError(code=1, controller=ConnectorEnum.JIRA.name,
                                      message='Error getting the JIRA attributes args. {}'.format(str(e)))
            try:
                if host and user and password:
                    self._connection = JIRAClient(host, user, password)
            except Exception as e:
                raise ControllerError(code=2, controller=ConnectorEnum.JIRA.name,
                                      message='Error instantiating the JIRA client. {}'.format(str(e)))

    def test_connection(self):
        try:
            response = self._connection.get_permissions()
        except Exception as e:
            return False
        if response is not None and isinstance(response, dict) and 'permissions' in response:
            return True
        else:
            return False

    def send_stored_data(self, data_list, **kwargs):
        result_list = []
        for obj in data_list:
            extra = {'controller': 'jira'}
            try:
                result = self.create_issue(self._plug.plug_action_specification.all()[0].value, obj)
                identifier = result['id']
                sent = True
            except:
                identifier = ""
                sent = False
            result_list.append({'data': dict(obj), 'response': '', 'sent': sent, 'identifier': identifier})
        return result_list

    def download_to_stored_data(self, connection_object=None, plug=None, issue=None, **kwargs):
        if issue is not None:
            issue_key = issue['key']
            _items = []
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug, object_id=issue_key)
            if not q.exists():
                for k, v in issue['fields'].items():
                    obj = StoredData(
                        connection=connection_object.connection, plug=plug, object_id=issue_key, name=k, value=v or ''
                    )
                    _items.append(obj)
            extra = {}
            is_stored = False
            raw = {}
            for item in _items:
                raw[item.name] = item.value
                item.save()
                is_stored = True
            result = [{'raw': raw, 'is_stored': is_stored, 'identifier': {'name': 'key', 'value': issue_key}}]
            return {'downloaded_data': result, 'last_source_record': issue_key}

    def get_projects(self):
        return self._connection.get_all_projects()

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
        fields['project'] = {'id': project_id}
        data = {'fields': fields}
        return self._connection.create_issue(data)

    def create_webhook(self):
        webhook = Webhook.objects.create(name='jira', url='', plug=self._plug, expiration='')
        url = '{0}/webhook/jira/{1}'.format(settings.WEBHOOK_HOST, webhook.id)
        key = self.get_key(self._plug.plug_action_specification.all()[0].value)
        data = {
            "name": "Gearplug Webhook",
            "url": url,
            "events": [
                "jira:issue_created",
            ],
            "jqlFilter": "Project = {}".format(key),
            "excludeIssueDetails": False
        }
        response = self._connection.create_webhook(data)
        if response:
            _id = response['self'].split('/')[-1]
            webhook.url = url
            webhook.generated_id = _id
            webhook.is_active = True
            webhook.save(update_fields=['url', 'generated_id', 'is_active'])
            return True
        else:
            webhook.is_deleted = True
            webhook.save(update_fields=['is_deleted', ])
            return False

    def get_key(self, project_id):
        for project in self.get_projects():
            if project['id'] == project_id:
                return project['key']
        return None

    def get_users(self):
        params = {
            'project': self.get_key(self._plug.plug_action_specification.all()[0].value)
        }
        response = self._connection.find_assignable_users(params)
        if response:
            return [{'id': u['name'], 'name': u['displayName']} for u in response]
        return []

    def get_meta(self):
        params = {
            'projectIds': self._plug.plug_action_specification.all()[0].value,
            'issuetypeNames': 'Task', 'expand': 'projects.issuetypes.fields'
        }
        meta = self._connection.get_create_issue_meta(params)
        exclude = ['attachment', 'project']
        users = self.get_users()

        def f(d, v):
            d.update({'id': v})
            return d

        _dict = [f(v, k) for k, v in meta['projects'][0]['issuetypes'][0]['fields'].items() if k not in exclude]
        for d in _dict:
            if d['id'] == 'reporter' or d['id'] == 'assignee':
                d['allowedValues'] = users
        return sorted(_dict, key=lambda i: i['name'])

    def get_target_fields(self, **kwargs):
        return self.get_meta()

    def get_mapping_fields(self, **kwargs):
        fields = self.get_meta()
        return [MapField(f, controller=ConnectorEnum.JIRA) for f in fields]

    def get_action_specification_options(self, action_specification_id):
        action_specification = ActionSpecification.objects.get(pk=action_specification_id)
        if action_specification.name.lower() == 'project_id':
            return tuple({'id': p['id'], 'name': p['name']} for p in self.get_projects())
        else:
            raise ControllerError("That specification doesn't belong to an action in this connector.")

    def do_webhook_process(self, body=None, post=None, force_update=False, **kwargs):
        issue = body['issue']
        plugs_to_update = Plug.objects.filter(
            Q(gear_source__is_active=True) | Q(is_tested=False),
            plug_action_specification__value__iexact=issue['fields']['project']['id'],
            plug_action_specification__action_specification__name__iexact='project_id',
            action__name='new issue', )
        for plug in plugs_to_update:
            self.create_connection(connection=plug.connection.related_connection, plug=plug)
            if self.test_connection():
                self.download_source_data(issue=issue)
            if not self._plug.is_tested:
                self._plug.is_tested = True
                self._plug.save(update_fields=['is_tested', ])
        return HttpResponse(status=200)

    def view_issue(self, issue_id):
        return self._connection.get_issue(issue_id)

    def delete_issue(self, issue_id):
        return self._connection.delete_issue(issue_id)

    def view_webhook(self, webhook_id):
        return self._connection.get_webhook(webhook_id)

    def delete_webhook(self, webhook_id):
        return self._connection.delete_webhook(webhook_id)

    @property
    def has_webhook(self):
        return True


class AsanaController(BaseController):
    _token = None
    _refresh_token = None
    _token_expiration_timestamp = None
    __refresh_url = 'https://app.asana.com/-/oauth_token'

    # # Codigo para traer proyectos por workspace en especifico
    # def proj_from_wp():
    #     headers = {
    #         'Authorization': 'Bearer {0}'.format(
    #             'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJhdXRob3JpemF0aW9uIjozODU0ODgxMjc0OTgxOTAsInNjb3BlIjoiZGVmYXVsdCIsImlhdCI6MTUwMTcwNzQ3NSwiZXhwIjoxNTAxNzExMDc1fQ.SDq4AF7I7miM5LbjOo1u9sDkQcYQkTNlnXt8K73VN34'),
    #     }
    #     # Request para obtener datos de usuario creador de la tarea
    #     resp_user_info = requests.get('https://app.asana.com/api/1.0/users/me',
    #                                   headers=headers)
    #
    #     # Request para obtener proyectos de los workspaces del usuario.
    #     params_proj = {('archived', 'false')}
    #     proj_list = {}
    #     for ws in resp_user_info.json()['data']['workspaces']:
    #         resp_user_wp = requests.get(
    #             'https://app.asana.com/api/1.0/workspaces/' + str(
    #                 ws['id']) + '/projects', headers=headers,
    #             params=params_proj)
    #         try:
    #             proj_list = {ws['id']: resp_user_wp.json()['data'][0]}
    #         except Exception as e:
    #             print('NO PROJECT IN WORKSPACE ', ws['id'])
    #     print(proj_list)

    def __init__(self, connection=None, plug=None, **kwargs):
        super(AsanaController, self).__init__(connection=connection, plug=plug, **kwargs)

    def create_connection(self, connection=None, plug=None, **kwargs):
        super(AsanaController, self).create_connection(connection=connection, plug=plug)
        if self._connection_object is not None:
            self._token = self._connection_object.token
            self._refresh_token = self._connection_object.refresh_token
            self._token_expiration_timestamp = self._connection_object.token_expiration_timestamp

    def test_connection(self):
        if self.is_token_expired():
            self.refresh_token()
        information = self.get_user_information()
        return information is not None

    def is_token_expired(self):
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
            new_token = requests.post(self.__refresh_url,
                                      data=data_refresh_token).json()
            print('3600 //', datetime.timedelta(seconds=float(new_token['expires_in'])).seconds,
                  type(datetime.timedelta(seconds=float(new_token['expires_in'])).seconds))
            self._connection_object.token = new_token['access_token']
            print('old_stamp',
                  self._connection_object.token_expiration_timestamp)
            self._connection_object.token_expiration_timestamp = time.time() + float(
                datetime.timedelta(
                    seconds=float(new_token['expires_in'])).seconds)
            print('new stamp',
                  self._connection_object.token_expiration_timestamp)
            # print('time', time.time(), type(time.time()))
            self._connection_object.save()
            self._token = self._connection_object.token
            return self._token
        except Exception as e:
            raise
            return None

    def get_user_information(self):
        # Headers para Request de usuario principal
        headers_1 = {  # data = {'resource', project.value,
            #             'target', url_base + url_path}
            #
            #     response = requests.post('https://app.asana.com/api/1.0/webhooks',
            #                              headers=headers, data=data)
            #     print("response", response.json())
            #     print("code", response.status_code)
            'Authorization': 'Bearer {0}'.format(self._token),
        }
        # Request para obtener datos de usuario creador de la tarea
        r = requests.get('https://app.asana.com/api/1.0/users/me',
                         headers=headers_1)
        try:
            response = r.json()
            return response['data']
        except Exception as e:
            print(e)
        return None

    def get_workspaces(self):
        try:
            return self.get_user_information()['workspaces']
        except Exception as e:
            print(e)
            return []

    def get_projects(self, workspace=None):
        # Diccionario de proyectos, manejo interno del metodo
        p_dict = {}

        # Lista de diccionario/s, esta lista es la que sera enviada a
        # get_action_specification_options.
        projects_list = []
        for ws in self.get_user_information()['workspaces']:
            headers_list_proj = {
                'Authorization': 'Bearer {}'.format(self._token)
            }
            params_proj = {
                ('archived', 'false')
            }
            aa_url = ('https://app.asana.com/api/1.0/workspaces/' + str(
                ws['id']) + '/projects')
            r_list_proj = requests.get(aa_url, headers=headers_list_proj,
                                       params=params_proj)
            temp_data_3 = r_list_proj.json()
            if temp_data_3['data']:
                return temp_data_3['data']
            else:
                raise ControllerError(code=1, message="No projects in this workspace")

    def get_action_specification_options(self, action_specification_id):
        action_specification = ActionSpecification.objects.get(
            pk=action_specification_id)
        if action_specification.name.lower() == 'project':
            return tuple(
                {'id': p['id'], 'name': p['name']} for p in self.get_projects())
        elif action_specification.name.lower() == 'workspace':
            return tuple(
                {'id': w['id'], 'name': w['name']} for w in
                self.get_workspaces())
        else:
            raise ControllerError(
                "That specification doesn't belong to an action in this connector.")

    def create_webhook(self):
        action = self._plug.action.name
        if action == 'new task created':
            project = self._plug.plug_action_specification.get(
                action_specification__name='project')
            # Creacion de Webhook
            webhook = Webhook.objects.create(name='asana', plug=self._plug, url='')
            # Verificar ngrok para determinar url_base
            url_base = settings.WEBHOOK_HOST
            url_path = reverse('home:webhook', kwargs={'connector': 'asana', 'webhook_id': webhook.id})
            headers = {
                'Authorization': 'Bearer {}'.format(self._token),
            }
            data = [('resource', int(project.value)),
                    ('target', url_base + url_path)]
            response = requests.post('https://app.asana.com/api/1.0/webhooks',
                                     headers=headers, data=data)
            if response.status_code == 201:
                webhook.url = url_base + url_path
                webhook.generated_id = response.json()['data']['id']
                webhook.is_active = True
                webhook.save(update_fields=['url', 'generated_id', 'is_active'])
            else:
                webhook.is_deleted = True
                webhook.save(update_fields=['is_deleted', ])
            return True
        return False

    def create_task(self, name=None, notes=None, assignee=None, followers=None,
                    **kwargs):
        try:
            workspace = self._plug.plug_action_specification.get(
                action_specification__name='workspace').value
        except Exception as e:
            workspace = None
        try:
            project = self._plug.plug_action_specification.get(
                action_specification__name='project').value
        except Exception as e:
            project = None
        headers = {'Authorization': 'Bearer {}'.format(self._token)}
        data = {}
        if name is not None:
            data['name'] = name
        if assignee is not None:
            data['assignee'] = {'id': assignee}
        if notes is not None:
            data['notes'] = notes
        if followers is not None:
            data['followers'] = followers
        if workspace is not None:
            data['workspace'] = workspace
        if project is not None:
            data['memberships'] = [{'project': project}, ]

        data_task = {'data': data}
        payload = json.dumps(data_task)
        r = requests.post('https://app.asana.com/api/1.0/tasks', data=payload,
                          headers=headers)
        return r

    def get_task(self, resource):
        if self.is_token_expired():
            self.refresh_token()
        # Headers para Request de usuario principal
        headers_comparing_data = {
            'Authorization': 'Bearer {}'.format(self._token),
        }

        # Request para obtener datos de usuario creador de la tarea
        r_comparing_data = requests.get(
            'https://app.asana.com/api/1.0/tasks/{0}'.format(
                resource), headers=headers_comparing_data)

        return r_comparing_data

    def download_to_stored_data(self, connection_object=None, plug=None,
                                event=None, **kwargs):
        if event is not None:
            event_resource = event['resource']
            q = StoredData.objects.filter(
                connection=connection_object.connection, plug=plug,
                object_id=event_resource)
            task_stored_data = []
            if not q.exists():
                task_data = self.get_task(event_resource).json()['data']
                for k, v in task_data.items():
                    if type(v) not in [list, dict]:
                        task_stored_data.append(
                            StoredData(connection=connection_object.connection,
                                       plug=plug, object_id=event_resource,
                                       name=k, value=v or ''))
                for key, value in task_data['memberships'][0].items():
                    if key == 'project':
                        for k, v in value.items():
                            task_stored_data.append(
                                StoredData(connection=connection_object.connection,
                                           plug=plug, object_id=event_resource,
                                           name='{0}_{1}'.format(key, k),
                                           value=v or ''))
            extra = {}
            for task in task_stored_data:
                try:
                    extra['status'] = 's'
                    extra = {'controller': 'asana'}
                    task.save()
                    self._log.info(
                        'Item ID: %s, Connection: %s, Plug: %s successfully stored.' % (
                            task.object_id, task.plug.id,
                            task.connection.id),
                        extra=extra)
                except Exception as e:
                    extra['status'] = 'f'
                    self._log.info(
                        'Item ID: %s, Connection: %s, Plug: %s failed.' % (
                            task.object_id, task.plug.id,
                            task.connection.id),
                        extra=extra)
            return True
        return False

    def get_target_fields(self, **kwargs):
        return [{'name': 'asignee', 'type': 'text', 'required': False},
                {'name': 'completed', 'type': 'text', 'required': True},
                {'name': 'due_on', 'type': 'text', 'required': False},
                {'name': 'due_at', 'type': 'text', 'required': False},
                {'name': 'followers', 'type': 'text', 'required': False},
                {'name': 'hearted', 'type': 'text', 'required': False},
                {'name': 'name', 'type': 'text', 'required': True},
                {'name': 'notes', 'type': 'text', 'required': False},
                {'name': 'tags', 'type': 'text', 'required': False}]

    def get_mapping_fields(self, **kwargs):
        fields = self.get_target_fields()
        return [MapField(f, controller=ConnectorEnum.Asana) for f in fields]

    def send_stored_data(self, source_data, target_fields, is_first=False):
        data_list = get_dict_with_source_data(source_data, target_fields)
        if self._plug is not None:
            obj_list = []
            extra = {'controller': 'Asana'}
            for item in data_list:
                task = self.create_task(**item)
                if task.status_code in [200, 201]:
                    extra['status'] = 's'
                    self._log.info('Item: %s successfully sent.' % (task.json()['data']['name']),
                                   extra=extra)
                    obj_list.append(task)
                else:
                    extra['status'] = 'f'
                    self._log.info('Item: failed to send.', extra=extra)
            return obj_list
        raise ControllerError("There's no plug")

    def do_webhook_process(self, body=None, POST=None, META=None, webhook_id=None, **kwargs):
        if 'HTTP_X_HOOK_SECRET' in META:
            response = HttpResponse()
            response['X-Hook-Secret'] = META['HTTP_X_HOOK_SECRET']
            response.status_code = 200
            return response
        events = body['events']
        for event in events:
            if event['type'] == 'task' and event['action'] == 'added':
                webhook = Webhook.objects.get(pk=webhook_id)
                if webhook.plug.gear_source.first().is_active or not webhook.plug.is_tested:
                    if not webhook.plug.is_tested:
                        webhook.plug.is_tested = True
                    self.create_connection(connection=webhook.plug.connection.related_connection, plug=webhook.plug)
                    if self.test_connection():
                        self.download_source_data(event=event)
        return HttpResponse(status=200)

    @property
    def has_webhook(self):
        return True
