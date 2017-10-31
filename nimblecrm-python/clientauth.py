import requests
import urllib
import json
import pprint
import webbrowser

OAUTH_URL = 'https://api.nimble.com/oauth/token'
REDIRECT_URL = 'https://813f6169.ngrok.io',
CODE_URL = 'https://api.nimble.com/oauth/authorize/'
CLIENT_ID = "EiexE2e4EIqYUycg1kIk005SX5yDPO" # api key
USER_SECRET = "1739.qwer"

class ClientAuth(object):

    def __init__(self, client_id=CLIENT_ID, client_secret=USER_SECRET, url=OAUTH_URL, redirect_url=REDIRECT_URL,
                 code_url=CODE_URL):
        self.client_id = client_id
        self.redirect_uri = redirect_url
        self.oauth_url = url
        self.code_url = code_url

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
        url = '{0}'.format(self.url)
        response = requests.request(method, url, headers=headers, data=data)
        return response

    def get_token(self):
        oauth_vars = {'client_id': self.client_id,
                      'redirect_uri': self.redirect_uri,
                      'grant_type': 'authorization_code'}
        grant_url = self.oauth_url + urllib.parse.urlencode(oauth_vars)
        webbrowser.open_new(grant_url)
        # print("Go to: {0} and authprize this app".format(grant_url))

    '''
        consumer_key = 'my_key_from_twitter'
        consumer_secret = 'my_secret_from_twitter'

        request_token_url = 'http://twitter.com/oauth/request_token'
        access_token_url = 'http://twitter.com/oauth/access_token'
        authorize_url = 'http://twitter.com/oauth/authorize'

        consumer = oauth.Consumer(consumer_key, consumer_secret)
        client = oauth.Client(consumer)

        # Step 1: Get a request token. This is a temporary token that is used for
        # having the user authorize an access token and to sign the request to obtain
        # said access token.


        if resp['status'] != '200':
            raise Exception("Invalid response %s." % resp['status'])

        request_token = dict(urlparse.parse_qsl(content))

        print("Request Token:")
        print("    - oauth_token        = %s" % request_token['oauth_token'])
        print("    - oauth_token_secret = %s" % request_token['oauth_token_secret'])

        # Step 2: Redirect to the provider. Since this is a CLI script we do not
        # redirect. In a web application you would redirect the user to the URL
        # below.

        print("Go to the following link in your browser:")
        print("%s?oauth_token=%s".format(authorize_url, request_token['oauth_token']))

        # After the user has granted access to you, the consumer, the provider will
        # redirect you to whatever URL you have told them to redirect to. You can
        # usually define this in the oauth_callback argument as well.
        accepted = 'n'
        while accepted.lower() == 'n':
            accepted = raw_input('Have you authorized me? (y/n) ')
        oauth_verifier = raw_input('What is the PIN? ')

        # Step 3: Once the consumer has redirected the user back to the oauth_callback
        # URL you can request the access token the user has approved. You use the
        # request token to sign this request. After this is done you throw away the
        # request token and use the access token returned. You should store this
        # access token somewhere safe, like a database, for future use.
        token = oauth.Token(request_token['oauth_token'],
                            request_token['oauth_token_secret'])
        token.set_verifier(oauth_verifier)
        client = oauth.Client(consumer, token)

        resp, content = client.request(access_token_url, "POST")
        access_token = dict(urlparse.parse_qsl(content))

        print
        "Access Token:"
        print
        "    - oauth_token        = %s" % access_token['oauth_token']
        print
        "    - oauth_token_secret = %s" % access_token['oauth_token_secret']
        print
        print
        "You may now access protected resources using the access tokens above."
        print

        # def auth_tool(self):
        #     client = oauth.Client(self.consumer)
        #     resp, content = client.request(self.oauth_url, "GET")
        #     print(resp)
        #     print(content)
        # def __init__(self, api_key=CLIENT_ID, client_secret=CLIENT_SECRET, url=OAUTH_URL, redirect_url=REDIRECT_URL):
        #     if api_key and url:
        #         self.client_id = api_key
        #         self.client_secret = client_secret
        #         self.url = url
        #         self.redirect_url = redirect_url
        #     else:
        #         raise
        #
        # def _post(self, endpoint, data=None):
        #     return self._request('post', endpoint, data=data)
        #
        # def _request(self, method, endpoint, data=None):
        #     headers = {
        #         'Accept': 'application/json',
        #         'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        #     }
        #     url = '{0}'.format(self.url)
        #     webbrowser.open_new(url=url)
        #     # response = requests.request(method, url, headers=headers, data=data)
        #     # print(response)
        #     # print(json.dumps(response))
        #     # return response
        #
        # def auth_tool(self):
        #     body = {
        #         "client_id": self.client_id,
        #         "code": 'code',
        #         "redirect_uri": self.redirect_url,
        #         "client_secret": self.client_secret,
        #         "grant_type": "authorization_code"
        #     }
        #     response = self._post(endpoint=self.url, data=body)
        #     return response
 
    '''
    ''''''