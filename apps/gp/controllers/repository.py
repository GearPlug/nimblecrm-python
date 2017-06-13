from apps.gp.controllers.base import BaseController
from apps.gp.controllers.exception import ControllerError
from apps.gp.controllers.utils import get_dict_with_source_data
from apps.gp.models import StoredData
from apps.gp.enum import ConnectorEnum
from apps.gp.map import MapField
import requests
from base64 import b64encode
from bitbucket.bitbucket import Bitbucket


class BitbucketController(BaseController):
    _connection = None
    API_BASE_URL = 'https://api.bitbucket.org'

    def __init__(self, *args, **kwargs):
        BaseController.__init__(self, *args, **kwargs)

    def create_connection(self, *args, **kwargs):
        if args:
            super(BitbucketController, self).create_connection(*args)
            if self._connection_object is not None:
                user = self._connection_object.connection_user
                password = self._connection_object.connection_password
        elif kwargs:
            user = kwargs.pop('connection_user', None)
            password = kwargs.pop('connection_password', None)
        else:
            user = password = None
        try:
            self._connection = Bitbucket(user, password)
            privileges = self._connection.get_privileges()[0]
        except Exception as e:
            print("Error getting the Bitbucket attributes")
            self._connection = None
            privileges = False
        return privileges

    def download_to_stored_data(self, connection_object=None, plug=None, issue=None, **kwargs):
        if issue is not None:
            issue_id = issue.pop('id')
            _items = []
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug,
                                          object_id=issue_id)
            if not q.exists():
                for k, v in issue.items():
                    obj = StoredData(connection=connection_object.connection, plug=plug,
                                     object_id=issue_id, name=k, value=v or '')
                    _items.append(obj)
            extra = {}
            for item in _items:
                extra['status'] = 's'
                extra = {'controller': 'bitbucket'}
                self._log.info('Item ID: %s, Connection: %s, Plug: %s successfully stored.' % (
                    item.object_id, item.plug.id, item.connection.id), extra=extra)
                item.save()
        return False

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
                success, result = self.create_issue(obj)
                print(success, result)
            extra = {'controller': 'bitbucket'}
            return
        raise ControllerError("Incomplete.")

    def _get_header(self):
        authorization = '{}:{}'.format(self._connection_object.connection_user,
                                       self._connection_object.connection_password)
        header = {'Accept': 'application/json',
                  'Authorization': 'Basic {0}'.format(b64encode(authorization.encode('UTF-8')).decode('UTF-8'))}
        return header

    def create_webhook(self, url='https://grplug.com/wizard/bitbucket/webhook/event/'):
        url = 'https://api.bitbucket.org/2.0/repositories/{}/{}/hooks'.format(self._connection_object.connection_user,
                                                                              self.get_repository_name())
        body = {
            'description': 'Gearplug Webhook',
            'url': url,
            'active': True,
            'events': [
                'issue:created'
            ]
        }
        r = requests.post(url, headers=self._get_header(), json=body)
        if r.status_code == 201:
            return True
        return False

    def get_repositories(self):
        url = '/2.0/repositories/{}'.format(self._connection_object.connection_user)
        r = self._request(url)
        return sorted(r['values'], key=lambda i: i['name']) if r else []

    def get_components(self):
        url = '/2.0/repositories/{}/{}/components'.format(self._connection_object.connection_user,
                                                          self.get_repository_name())
        r = self._request(url)
        return r['values'] if r else []

    def get_milestones(self):
        url = '/2.0/repositories/{}/{}/milestones'.format(self._connection_object.connection_user,
                                                          self.get_repository_name())
        r = self._request(url)
        return r['values'] if r else []

    def get_versions(self):
        url = '/2.0/repositories/{}/{}/versions'.format(self._connection_object.connection_user,
                                                        self.get_repository_name())
        r = self._request(url)
        return r['values'] if r else []

    def _get_repository(self, get_id):
        for specification in self._plug.plug_specification.all():
            if specification.action_specification.name == ('repository_id' if get_id else 'repository_name'):
                return specification.value

    def get_repository_id(self):
        return self._get_repository(True)

    def get_repository_name(self):
        return self._get_repository(False)

    def _request(self, url):
        payload = {
            'pagelen': '100'
        }
        r = requests.get(self.API_BASE_URL + url, headers=self._get_header(), params=payload)
        if r.status_code == requests.codes.ok:
            return r.json()
        return None

    def create_issue(self, fields):
        self._connection.repo_slug = self.get_repository_name()
        return self._connection.issue.create(**fields)

    def get_meta(self):
        return [{
            'name': 'title',
            'required': True,
            'type': 'text',

        }, {
            'name': 'content',
            'required': False,
            'type': 'text',
        }, {
            'name': 'kind',
            'required': True,
            'type': 'choices',
            'values': [
                'bug',
                'enhancement',
                'proposal',
                'task'
            ]
        }, {
            'name': 'priority',
            'required': True,
            'type': 'choices',
            'values': [
                'trivial',
                'minor',
                'major',
                'critical',
                'blocker'
            ]
        }, {
            'name': 'status',
            'required': False,
            'type': 'choices',
            'values': [
                'new',
                'open',
                'resolved',
                'on hold',
                'invalid',
                'duplicate',
                'wontfix'
            ]
        }, {
            'name': 'component',
            'required': False,
            'type': 'choices',
            'values': [c['name'] for c in self.get_components()]
        }, {
            'name': 'milestone',
            'required': False,
            'type': 'choices',
            'values': [m['name'] for m in self.get_milestones()]
        }, {
            'name': 'version',
            'required': False,
            'type': 'choices',
            'values': [v['name'] for v in self.get_versions()]
        }]

    def get_target_fields(self):
        return self.get_meta()

    def get_mapping_fields(self, **kwargs):
        fields = self.get_meta()
        return [MapField(f, controller=ConnectorEnum.Bitbucket) for f in fields]
