import requests

class Client(object):
    BASE_URL = 'https://api.typeform.com/'
    _VALID_VERSIONS = ['v1', ]

    def __init__(self, api_key, version=None):
        self.api_key = api_key
        if version not in self._VALID_VERSIONS:
            self.version = self._VALID_VERSIONS[0]

    def _get(self, endpoint, params=None):
        return self._request('GET', endpoint, params)

    def _request(self, method, endpoint, params=None, data=None):
        url = '{0}{1}/{2}'.format(self.BASE_URL, self.version, endpoint)
        print(url)
        response = requests.request(method, url, params=params, json=data)
        r = response.json()
        if response.status_code in [403, 404]:
            if 'message' in r:
                raise Exception(r['message'])
            else:
                if 'code' in r:
                    raise Exception(r['description'])
                raise Exception('Unexpected error.')
        return r

    def get_form_uid(self, url_form):
        """Returns addresses registered by the user.
        Args:
            url_form:
        Returns:
            A string.
        """
        list_url = url_form.split("/to/")
        typeform_uid = list_url[1]
        return typeform_uid

    def get_form_information(self, uid=None, url=None):
        """Returns addresses registered by the user.
        Args:
            typeform_uid:
        Returns:
            A dict.
        """
        if uid is None:
            if url is None:
                raise Exception('You must provide either an UID or Form URL.')
            else:
                uid = self.get_form_uid(url)
        params = {'key': self.api_key}
        return self._get('form/{}'.format(uid), params=params)

    def get_form_stats(self, uid=None, url=None, form=None):
        """Returns stats of form.
        Args:
            uid:
            url:
        Returns:
            A dict.
        """
        if form is not None:
            return form['stats']
        return self.get_form_information(uid=uid, url=url)['stats']

    def get_form_questions(self, uid=None, url=None, form=None):
        """Returns questions of form.
        Args:
            uid:
            url:
        Returns:
            A dict.
        """
        if form is not None:
            return form['questions']
        return self.get_form_information(uid=uid, url=url)['questions']

    def get_form_metadata(self, uid=None, url=None, form=None):
        """Returns metadata of form.
        Args:
            uid:
            url:
        Returns:
            A dict.
        """
        if form is not None:
            return form['responses']
        return self.get_form_information(uid=uid, url=url)['responses']

    def get_form_answers(self, uid=None, url=None, form=None):
        """Returns answers of form.
        Args:
            uid:
            url:
        Returns:
            A list.
        """
        if form is None:
            form = self.get_form_information(uid=uid, url=url)
        return [answers['answers'] for answers in form['responses']]

    def get_forms(self):
        """Returns all forms
        Args:
        Returns:
            A dict.
        """
        params = {'key': self.api_key}
        return self._get('forms?key={0}'.format(self.api_key), params=params)