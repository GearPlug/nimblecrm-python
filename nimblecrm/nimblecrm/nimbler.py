import requests
import exception
from enumerator import ErrorEnum

class Client(object):
    _VALID_VERSIONS = ['v1']

    def __init__(self, access_token=None, base_url=None):

        self.api_key = access_token
        self.base_url = base_url

    def _post(self, endpoint, data=None):
        return self._request('POST', endpoint, data=data)

    def _get(self, endpoint):
        return self._request('GET', endpoint)

    def _put(self, endpoint, data=None):
        return self._request('PUT', endpoint, data=data)

    def _delete(self, endpoint, data=None):
        return self._request('DELETE', endpoint, data=data)

    def _request(self, method, endpoint, data=None):
        url = '{0}/{1}'.format(self.base_url, endpoint)
        headers = {'Authorization': 'Bearer {0}'.format(self.api_key),
                   "Content-Type": "application/json",
                   }
        response = requests.request(method, url, headers=headers, data=data)
        return self._parse(response)

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
                raise exception.UnexpectedError('Error:{0}{1}.Message{2}'.format(code, response.status_code, message))
            if error_enum == ErrorEnum.Forbidden:
                raise exception.Forbidden(message)
            if error_enum == ErrorEnum.Not_Found:
                raise exception.Not_Found(message)
            if error_enum == ErrorEnum.Payment_Required:
                raise exception.Payment_Required(message)
            if error_enum == ErrorEnum.Internal_Server_Error:
                raise exception.Internal_Server_Error(message)
            if error_enum == ErrorEnum.Service_Unavailable:
                raise exception.Service_Unavailable(message)
            if error_enum == ErrorEnum.Bad_Request:
                raise exception.Bad_Request(message)
            if error_enum == ErrorEnum.Unauthorized:
                raise exception.Unauthorized(message)
            if error_enum == ErrorEnum.InvalidParameters:
                raise exception.Unauthorized(message)
            if error_enum == ErrorEnum.QuotaExceeded:
                raise exception.Unauthorized(message)
            else:
                raise exception.BaseError('Error: {0}{1}. Message {2}'.format(code, response.status_code, message))
            return data
        else:
            return response

    def get_contact_list(self):
        """Returns all contacts.
        """
        endpoint = 'contacts'
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
