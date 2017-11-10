import requests
from .exceptions import *
from .enumerator import ErrorEnum
from .clientauth import ClientAuth
import urllib.parse
from urllib.parse import parse_qsl
import json
from datetime import datetime, timedelta


class Client(object):
    _VALID_VERSIONS = ['v1']

    def __init__(self,
                 client_id=None,
                 client_secret=None,
                 redirect_url=None,
                 oauth_url=None,
                 base_url=None,
                 code_url=None,
                 token=None,
                 token_expiration_time=None,
                 refresh_token=None):

        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_url
        self.oauth_url = oauth_url
        self.code_url = code_url
        self.base_url = base_url
        self.code = None
        self.token = token
        self.token_expiration_time = token_expiration_time
        self.refresh_token = refresh_token

    def _post(self, endpoint, data=None):
        return self._request('POST', endpoint, data=data)

    def _get(self, endpoint, payload=None):
        return self._request('GET', endpoint, data=payload)

    def _put(self, endpoint, data=None):
        return self._request('PUT', endpoint, data=data)

    def _delete(self, endpoint, data=None):
        return self._request('DELETE', endpoint, data=data)

    def _request(self, method, endpoint, data=None):
        try:
            self.token_expiration_checker()
        except Exception as e:
            print(e)

        url = '{0}/{1}'.format(self.base_url, endpoint)
        headers = {
            'Authorization': 'Bearer {0}'.format(self.token),
            'Content-Type': 'application/json; charset=utf-8',
        }
        print('123123', url)
        response = requests.request(method, url, headers=headers, data=data)
        return (response)

    def _parse(self, response):
        if not response.ok:
            try:
                data = response.json()
                if 'message' in data['errors']['/'] and 'code' in data:
                    message = data['errors']['/']['message']
                    code = data['errors']['/']['code']
            except:
                code = response.status_code
                message = ""
            try:
                try:
                    error_enum = ErrorEnum(response.status_code)
                except Exception as e:
                    print(e)
            except Exception:
                raise UnexpectedError('Error:{0}{1}.Message{2}'.format(code, response.status_code, message))
            if error_enum == ErrorEnum.Forbidden:
                raise Forbidden(message)
            if error_enum == ErrorEnum.Not_Found:
                raise Not_Found(message)
            if error_enum == ErrorEnum.Payment_Required:
                raise Payment_Required(message)
            if error_enum == ErrorEnum.Internal_Server_Error:
                raise Internal_Server_Error(message)
            if error_enum == ErrorEnum.Service_Unavailable:
                raise Service_Unavailable(message)
            if error_enum == ErrorEnum.Bad_Request:
                raise Bad_Request(message)
            if error_enum == ErrorEnum.Unauthorized:
                raise Unauthorized(message)
            if error_enum == ErrorEnum.InvalidParameters:
                raise Unauthorized(message)
            if error_enum == ErrorEnum.QuotaExceeded:
                raise Unauthorized(message)
            else:
                raise BaseError('Error: {0}{1}. Message {2}'.format(code, response.status_code, message))
            return data
        else:
            return response

    def get_token(self, code):
        ca = ClientAuth(
            client_id=self.client_id,
            client_secret=self.client_secret,
            oauth_url=self.oauth_url,
            redirect_url=self.redirect_uri,
            code_url=None,
            base_url=self.base_url)
        return ca.get_token(code=code)

    def token_expiration_checker(self):
        if datetime.now() > self.token_expiration_time:
            self.to_refresh_token()
        else:
            print('token still valid.')

    def to_refresh_token(self):
        oauth_vars = {'client_id': self.client_id,
                      'client_secret': self.client_secret,
                      'redirect_uri': self.redirect_uri,
                      'refresh_token': self.refresh_token,
                      'grant_type': 'refresh_token'}
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        }
        try:
            token = requests.post(url='https://api.nimble.com/oauth/token', headers=headers, params=oauth_vars)
            token = token.json()
            self.token = token['access_token']
            self.token_expiration_time = token['expires_in']
            self.refresh_token = token['refresh_token']
        except Exception as e:
            print(e)

    def get_contact_list(self):
        """Returns all contacts.
        """
        endpoint = 'contacts'
        try:
            return self._get(endpoint=endpoint)
        except Exception as e:
            print(e)

    def get_persons(self):
        endpoint = "contacts?query="
        values = {"record type": {"is": "person"}}
        values = json.dumps(values)
        values = urllib.parse.quote_plus(values)
        endpoint = endpoint+values
        try:
            return self._get(endpoint=endpoint)
        except Exception as e:
            print(e)

    def get_organizations(self):
        endpoint = "contacts?query="
        values = {"record type": {"is": "company"}}
        values = json.dumps(values)
        values = urllib.parse.quote_plus(values)
        endpoint = endpoint+values
        try:
            return self._get(endpoint=endpoint)
        except Exception as e:
            print(e)

    def get_contact(self, *args):
        """Returns indicated contacts detailed info.
        Args:
            args: ID or list of IDs of contacts.
        """
        if args:
            endpoint = 'contact/{0}'.format(','.join(args))
            try:
                return self._get(endpoint=endpoint)
            except Exception as e:
                print(e)
        else:
            raise ErrorEnum.DataRequired("Please verified ID or IDs of contact/s to get.")

    def create_contact(self, data):
        """Returns response for contact creation attemp.
        Args will be a list of dicts.
        Args: as JSON in request body
        data =
        '{
            "fields":
                {
                "first name":
                    [{"value": "fumarola", "modifier": ""}],
                "last name":
                    [{"value": "McMcloyd", "modifier": ""}],
                "phone":
                    [
                    {"modifier": "work","value": "123123123"},
                    {"modifier": "work","value": "2222"}
                    ]
                },
            "record_type": "person"
        }'
        """
        if data:
            endpoint = 'contact'
            try:
                return self._post(endpoint=endpoint, data=data)
            except Exception as e:
                print(e)
        else:
            raise ErrorEnum.DataRequired("Please verified that all data required for contact creation is present.")

    def full_contact_update(self, id, data):
        """Returns response for contact update attemp.
        Args will be a list of dicts, the number one (1) inside the endpoint url indicates that
        we want to update all fields for certain modifier.
        Args: as JSON in request body
            args:{
            'fields': {'first_name':'', 'value':'', 'phone':[{'modifier':'work', 'value':'5553333222'},
                                                             {'modifier':'house', 'value':'777552235'}]
                      },
            }
        """
        if data and id:
            endpoint = 'contact/{0}?replace=1'.format(id)
            try:
                return self._put(endpoint=endpoint, data=data)
            except Exception as e:
                print(e)
        else:
            raise ErrorEnum.DataRequired("Please verified that all data required for contact update is present.")

    def partial_contact_update(self, id, data):
        """Returns response for contact update attemp.
        Args will be a list of dicts, the number one (1) inside the endpoint url indicates that
        we want to update specifics fields with specifics modifiers.
        Args: as JSON in request body
            args:{
            'fields': {'first_name':'', 'value':'', 'phone':[{'modifier':'work', 'value':'5553333222'},
                                                             {'modifier':'house', 'value':'777552235'}]
                      },
            }
        """
        if data and id:
            endpoint = 'contact/{0}?replace=0'.format(id)
            try:
                return self._put(endpoint=endpoint, data=data)
            except Exception as e:
                print(e)
        else:
            raise ErrorEnum.DataRequired("Please verified that all data required for contact update is present.")

    def delete_contact(self, id):
        """Returns response for contact creation attemp.
        Args will be a list of dicts.
        Args: None, the ids of the contacts to Delete are sent on the endpoint url.
        """
        if id:
            data = '{}'
            endpoint = 'contact/{0}'.format(id)
            try:
                return self._delete(endpoint=endpoint, data=data)
            except Exception as e:
                print(e)
        else:
            raise ErrorEnum.DataRequired("Please verified that the ids were sent.")

    def create_task(self, data):
        """Returns response for contact creation attemp.
        Args will be a list of dicts.
        Args:
            {
            "due_date": "2013-04-04 13:50",
            "notes": "Blah blah blah blah u0441\u043a\u0438\u0439 \u0442\u0435\u043a\u0441\u0442 8168949",
            "related_to": [
                "508a4750084abd28bc00016f"
            ],
            "subject": "Hello task! 2423056"
            }
        """
        if data:
            endpoint = 'activities/task'
            try:
                return self._post(endpoint=endpoint, data=data)
            except Exception as e:
                print(e)
        else:
            raise ErrorEnum.DataRequired("Please verified that the ids were sent.")

    def get_last_register(self, limit=None, date=None):
        """
        TODO
        Returns register from certain date.
        query:
        {"created": {"range": {"start_date": "2012-10-16","end_date": "2012-10-18"}}}

        """
        endpoint = 'contacts'
        values = {
            'query': {"created": {"range": {"start_date": "2012-10-16","end_date": "2012-10-18"}}},
            'per_page': limit,
            'fields': 'created'
        }
        data = urllib.parse.urlencode(values).encode('utf-8')
        endpoint = endpoint+data
        try:
            return self._get(endpoint=endpoint)
        except Exception as e:
            print(e)
