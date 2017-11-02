import requests
import urllib
import json
import pprint
import webbrowser

class ClientAuth(object):

    def __init__(self, client_id=None, client_secret=None, oauth_url=None, redirect_url=None, code_url=None, 
                base_url=None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_url
        self.oauth_url = oauth_url
        self.code_url = code_url
        self.base_url = base_url

    def get_code(self):
        '''
        GET https://api.nimble.com/oauth/authorize
        :return:
        '''
        code_vars = {'client_id': self.client_id,
                      'redirect_uri': self.redirect_uri,
                      'response_type': 'code'}
        code_url = self.code_url + urllib.parse.urlencode(code_vars)
        webbrowser.open_new(code_url)

    def _post(self, endpoint, data=None):

        return self._request('POST', endpoint, data=data)

    def _get(self, endpoint, data=None):

        return self._request('GET', endpoint, data=data)

    def _request(self, method, endpoint, data=None):
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        }
        url = '{0}/{1}'.format(self.base_url, endpoint)
        response = requests.request(method, url, headers=headers, data=data)
        return response

    def get_token(self, code):
        oauth_vars = {'client_id': self.client_id,
                      'client_secret': self.client_secret,
                      'redirect_uri': self.redirect_uri,
                      'code': code,
                      'grant_type': 'authorization_code'}
        try:
            response = self._get(endpoint=self.oauth_url, data=oauth_vars)
            return response
        except Exception as e:
            print(e)
