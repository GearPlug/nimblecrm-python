from apps.gp.controllers.base import BaseController
from apps.gp.controllers.exception import ControllerError
from apps.gp.controllers.utils import get_dict_with_source_data
from apps.gp.models import StoredData, ActionSpecification, Webhook
from apps.gp.enum import ConnectorEnum
from apps.gp.map import MapField
import requests
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError
from django.conf import settings
from django.http import HttpResponse
from bitbucket.client import Client as BibucketClient


class BitbucketController(BaseController):
    _connection = None
    _repo_id = None
    _repo_slug = None
    _user = None
    _password = None

    def __init__(self, connection=None, plug=None):
        BaseController.__init__(self, connection=connection, plug=plug)

    def create_connection(self, connection=None, plug=None):
        super(BitbucketController, self).create_connection(connection=connection, plug=plug)
        if self._connection_object is not None:
            try:
                self._user = self._connection_object.connection_user
                self._password = self._connection_object.connection_password
            except Exception as e:
                raise ControllerError(
                    code=1001,
                    controller=ConnectorEnum.Bitbucket,
                    message='The attributes necessary to make the connection were not obtained. {}'.format(str(e)))
        else:
            raise ControllerError(
                code=1002,
                controller=ConnectorEnum.Bitbucket,
                message='The controller is not instantiated correctly.')
        try:
            self._connection = BibucketClient(self._user, self._password)
        except Exception as e:
            raise ControllerError(
                code=1003,
                controller=ConnectorEnum.Bitbucket,
                message='Error in the instantiation of the client. {}'.format(str(e)))
        try:
            if self._plug is not None:
                self._repo_id = self._plug.plug_action_specification.filter(
                    action_specification__name='repository').first().value
                self._repo_slug = self.get_repository_name(self._repo_id)
        except Exception as e:
            raise ControllerError(
                code=1005,
                controller=ConnectorEnum.Bitbucket,
                message='Error while choossing specifications. {}'.format(str(e)))

    def test_connection(self):
        try:
            user_info = self._connection.get_user()
        except Exception as e:
            raise ControllerError(
                code=1004,
                controller=ConnectorEnum.Bitbucket,
                message='Error in the connection test. {}'.format(str(e)))
        if user_info is not None and 'account_id' in user_info and user_info['account_id'] != '':
            return True
        else:
            return False

    def download_to_stored_data(self, connection_object=None, plug=None, issue=None, **kwargs):
        if issue is not None:
            issue_id = issue['id']
            last_source_record = issue['updated_on']
            _items = []
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug, object_id=issue_id)
            if not q.exists():
                for k, v in issue.items():
                    obj = StoredData(connection=connection_object.connection, plug=plug, object_id=issue_id, name=k,
                                     value=v or '')
                    _items.append(obj)
            result_data = []
            is_stored = False
            for item in _items:
                item.save()
                is_stored = True
            result_data.append({'raw': issue, 'is_stored': is_stored, 'identifier': {'name': 'id', 'value': issue_id}})
            return {'downloaded_data': result_data, 'last_source_record': last_source_record}

    def send_stored_data(self, data_list, **kwargs):
        obj_list = []
        for obj in data_list:
            result = self.create_issue(obj)
            try:
                sent = True
                response = str(result)
                identifier = result['id']
            except Exception as e:
                sent = False
                response = str(e)
                identifier = '-1'
            obj_list.append({'data': dict(obj), 'response': response, 'sent': sent, 'identifier': identifier})
        return obj_list

    def create_webhook(self):
        webhook = Webhook.objects.create(name='bitbucket', url='', plug=self._plug, expiration='')
        url = "{}/webhook/bitbucket/{}/".format(settings.CURRENT_HOST, webhook.id)
        data = {
            'description': 'Gearplug Webhook',
            'url': url,
            'active': True,
            'events': [
                'issue:created'
            ]
        }
        response = self._connection.create_webhook(self._repo_slug, data)
        if response:
            _id = response['uuid']
            webhook.url = url
            webhook.generated_id = _id
            webhook.is_active = True
            webhook.save(update_fields=['url', 'generated_id', 'is_active'])
            return True
        else:
            webhook.is_deleted = True
            webhook.save(update_fields=['is_deleted', ])
            return False

    def delete_webhook(self, id_webhook):
        return self._connection.delete_webhook(self._repo_slug, id_webhook)

    def view_webhook(self, id_webhook):
        return self._connection.get_webhook(self._repo_slug, id_webhook)

    def do_webhook_process(self, body=None, POST=None, META=None, webhook_id=None, **kwargs):
        webhook = Webhook.objects.get(pk=webhook_id)
        if webhook.plug.gear_source.first().is_active or not webhook.plug.is_tested:
            if not webhook.plug.is_tested:
                webhook.plug.is_tested = True
            self.create_connection(connection=webhook.plug.connection.related_connection, plug=webhook.plug)
            if self.test_connection():
                self.download_source_data(issue=body['issue'])
                webhook.plug.save()
        return HttpResponse(status=200)

    def get_repositories(self):
        r = self._connection.get_repositories({'pagelen': 100})
        return sorted(r['values'], key=lambda i: i['name']) if r else []

    def get_repository_name(self, _id):
        r = self._connection.get_repositories({'pagelen': 100})
        _name = ""
        for r in r['values']:
            if r['uuid'] == _id:
                _name = r['name']
        return _name

    def get_components(self):
        r = self._connection.get_repository_components(self._repo_slug, params={'pagelen': 100})
        return r['values'] if r else []

    def get_milestones(self):
        r = self._connection.get_repository_milestones(self._repo_slug, params={'pagelen': 100})
        return r['values'] if r else []

    def get_versions(self):
        r = self._connection.get_repository_versions(self._repo_slug, params={'pagelen': 100})
        return r['values'] if r else []

    def create_issue(self, fields):
        return self._connection.create_issue(self._repo_slug, fields)

    def view_issue(self, issue_id):
        return self._connection.get_issue(self._repo_slug, issue_id)

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

    def get_action_specification_options(self, action_specification_id):
        action_specification = ActionSpecification.objects.get(pk=action_specification_id)
        if action_specification.name.lower() in ['repository', 'repository']:
            tup = tuple({'id': p['uuid'], 'name': p['name']} for p in self.get_repositories())
            return tup
        else:
            raise ControllerError("That specification doesn't belong to an action in this connector.")

    @property
    def has_webhook(self):
        return True


class GitLabController(BaseController):
    _token = None
    _refresh_token = None

    def __init__(self, connection=None, plug=None, **kwargs):
        super(GitLabController, self).__init__(connection=connection, plug=plug, **kwargs)

    def do_get(self, url, data=None):
        bearer = 'Bearer {0}'.format(self._token)

        headers = {
            'Authorization': bearer,
        }

        response = requests.get(url, headers=headers, data=data)

        return response

    def do_post(self, url, data=None):
        bearer = 'Bearer {0}'.format(self._token)

        headers = {
            'Authorization': bearer,
        }

        response = requests.post(url, headers=headers, data=data)

        return response

    def refresh_token(self):

        params = {
            "grant_type": "refresh_token",
            "refresh_token": self._refresh_token,
            "scope": "api"
        }

        response = requests.post("https://gitlab.com/oauth/token",
                                 data=params)

        token = response.json()
        try:
            self._token = token['access_token']
            self._refresh_token = token['refresh_token']
            return True
        except Exception as e:
            print(e)
            return False

    def create_connection(self, connection=None, plug=None, **kwargs):
        super(GitLabController, self).create_connection(connection=connection, plug=plug)
        if self._connection_object is not None:
            self._token = self._connection_object.token
            self._refresh_token = self._connection_object.refresh_token

    def test_connection(self):
        try:
            if self.get_user_id() is not None:
                return True
        except Exception as e:
            return False

    def get_user_id(self):
        url = 'https://gitlab.com/api/v4/user'
        try:
            response = self.do_get(url)
        except InvalidGrantError:
            self.refresh_token()

        return response.json()['id']

    def get_projects(self):

        user_id = self.get_user_id()
        url = 'https://gitlab.com/api/v4/users/{0}/projects'.format(user_id)
        try:
            response = self.do_get(url)
        except InvalidGrantError:
            self.refresh_token()
        return response.json()

    def create_issue(self, params=None):

        project = self._plug.plug_action_specification.get(
            action_specification__name='project')

        project = project.value
        params = (
            ('title', dict(params)['title']),
            ('id', '0001'),
            ('name', dict(params)['name']),
            ('description', dict(params)['description']),
            ('notes', dict(params)['notes']),
            ('labels', dict(params)['labels']),
            ('weight', dict(params)['weight']),
        )
        url = 'https://gitlab.com/api/v4/projects/{0}/issues'.format(project)
        try:
            response = self.do_post(url, params)
        except InvalidGrantError:
            self.refresh_token()
        return response

    def download_to_stored_data(self, connection_object=None, plug=None, issue=None, **kwargs):
        if issue is not None:
            issue_data = issue['object_attributes']
            issue_id = issue_data['id']
            _items = []
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug,
                                          object_id=issue_id)
            if not q.exists():
                for k, v in issue_data.items():
                    obj = StoredData(connection=connection_object.connection, plug=plug,
                                     object_id=issue_id, name=k, value=v or '')
                    _items.append(obj)
            extra = {}
            for item in _items:
                extra['status'] = 's'
                extra = {'controller': 'gitlab'}
                self._log.info('Item ID: %s, Connection: %s, Plug: %s successfully stored.' % (
                    item.object_id, item.plug.id, item.connection.id), extra=extra)
                item.save()
        return False

    def send_stored_data(self, source_data, target_fields, is_first=False):
        data_list = get_dict_with_source_data(source_data, target_fields)
        if is_first:
            if data_list:
                try:
                    data_list = [data_list[-1]]
                except:
                    data_list = []
        if self._plug is not None:
            for obj in data_list:
                result = self.create_issue(obj)
            extra = {'controller': 'gitlab'}
            return
        raise ControllerError("Incomplete.")

    def create_webhook(self):
        action = self._plug.action.name
        if action == 'new issue':
            project = self._plug.plug_action_specification.get(
                action_specification__name='project')
            # Creacion de Webhook
            webhook = Webhook.objects.create(name='gitlab', plug=self._plug, url='')
            redirect_uri = "{0}/webhook/gitlab/{1}/".format(settings.CURRENT_HOST, webhook.id)
            url_listen_webhook = redirect_uri

            project = project.value
            params = (
                ('url', url_listen_webhook),
                ('issues_events', True),
            )
            endpoint = 'https://gitlab.com/api/v4/projects/{0}/hooks'.format(project)
            try:
                response = self.do_post(endpoint, params)
            except InvalidGrantError:
                self.refresh_token()
            try:
                if response.status_code == 201 or response.status_code == 200:
                    webhook.url = redirect_uri
                    webhook.generated_id = response.json()['id']
                    webhook.is_active = True
                    webhook.save(update_fields=['url', 'generated_id', 'is_active'])
                else:
                    webhook.is_deleted = True
                    webhook.save(update_fields=['is_deleted', ])
                return True
            except Exception as e:
                print(e)
        return False

    def send_stored_data(self, source_data, target_fields, is_first=False):
        data_list = get_dict_with_source_data(source_data, target_fields)
        if self._plug is not None:
            obj_list = []
            extra = {'controller': 'gitlab'}
            for item in data_list:
                try:
                    response = self.create_issue(item)
                    self._log.info(
                        'Item: %s successfully sent.' % (list(item.items())[0][1]), extra=extra)
                    obj_list.append(id)
                except Exception as e:
                    print(e)
                    extra['status'] = 'f'
                    self._log.info(
                        'Item: %s failed to send.' % (list(item.items())[0][1]), extra=extra)
                    return obj_list
        raise ControllerError("There's no plug")

    def get_target_fields(self):
        return [{'name': 'name', 'type': 'varchar', 'required': True},
                {'name': 'id', 'type': 'varchar', 'required': True},
                {'name': 'description', 'type': 'varchar', 'required': False},
                {'name': 'crated_at', 'type': 'varchar', 'required': False},
                {'name': 'author', 'type': 'varchar', 'required': False},
                {'name': 'state', 'type': 'varchar', 'required': False},
                {'name': 'url', 'type': 'varchar', 'required': False},
                {'name': 'project', 'type': 'varchar', 'required': False}
                ]

    def get_mapping_fields(self, **kwargs):
        fields = self.get_target_fields()
        return [MapField(f, controller=ConnectorEnum.GitLab) for f in fields]

    def get_action_specification_options(self, action_specification_id):
        action_specification = ActionSpecification.objects.get(
            pk=action_specification_id)
        if action_specification.name.lower() == 'project':
            return tuple(
                {'id': p['id'], 'name': p['name']} for p in self.get_projects())
        else:
            raise ControllerError("That specification doesn't belong to an action in this connector.")

    def do_webhook_process(self, body=None, POST=None, META=None, webhook_id=None, **kwargs):
        webhook = Webhook.objects.get(pk=webhook_id)
        if webhook.plug.gear_source.first().is_active or not webhook.plug.is_tested:
            if not webhook.plug.is_tested:
                webhook.plug.is_tested = True
            self.create_connection(connection=webhook.plug.connection.related_connection, plug=webhook.plug)
            if self.test_connection():
                self.download_source_data(issue=body)
                webhook.plug.save()
        return HttpResponse(status=200)
