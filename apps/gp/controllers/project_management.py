from apps.gp.controllers.base import BaseController
from apps.gp.controllers.exception import ControllerError
from apps.gp.controllers.utils import get_dict_with_source_data
from apps.gp.models import StoredData

import requests
from base64 import b64encode
from jira import JIRA


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
                res = self.create_issue(self._plug.plug_specification.all()[0].value, obj)
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
        key = self.get_key(self._plug.plug_specification.all()[0].value)
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
            'project': self.get_key(self._plug.plug_specification.all()[0].value)
        }

        url = 'http://jira.grplug.com:8080/rest/api/2/user/assignable/search'
        r = requests.get(url, headers=self._get_header(), params=payload)
        if r.status_code == requests.codes.ok:
            return [{'id': u['name'], 'name': u['displayName']} for u in r.json()]
        return []

    def get_meta(self):
        meta = self._connection.createmeta(projectIds=self._plug.plug_specification.all()[0].value,
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
