from apps.gp.controllers.base import BaseController
from apps.gp.controllers.exception import ControllerError
from apps.gp.controllers.utils import get_dict_with_source_data
from django.conf import settings

import tweepy


class TwitterController(BaseController):
    _token = None
    _token_secret = None

    def __init__(self, *args, **kwargs):
        BaseController.__init__(self, *args, **kwargs)

    def create_connection(self, *args, **kwargs):
        if args:
            super(TwitterController, self).create_connection(*args)
            if self._connection_object is not None:
                try:
                    self._token = self._connection_object.token
                    self._token_secret = self._connection_object.token_secret
                except Exception as e:
                    print("Error getting the Twitter Token")
                    print(e)
        elif kwargs:
            if 'token' in kwargs and 'token_secret' in kwargs:
                self._token = kwargs['token']
                self._token_secret = kwargs['token_secret']
        me = None
        if self._token and self._token_secret:
            api = tweepy.API(self.get_twitter_auth())
            me = api.me()
        return me is not None

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
                self.post_tweet(obj)
            extra = {'controller': 'twitter'}
        raise ControllerError("Incomplete.")

    def get_twitter_auth(self):
        consumer_key = settings.TWITTER_CLIENT_ID
        consumer_secret = settings.TWITTER_CLIENT_SECRET
        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(self._token, self._token_secret)
        return auth

    def post_tweet(self, item):
        api = tweepy.API(self.get_twitter_auth())
        api.update_status(**item)

    def get_target_fields(self, **kwargs):
        return [{
            'name': 'status',
            'required': True,
            'type': 'text',
        }, {
            'name': 'in_reply_to_status_id',
            'required': False,
            'type': 'text',
        }, {
            'name': 'lat',
            'required': False,
            'type': 'text',
        }, {
            'name': 'long',
            'required': False,
            'type': 'text',
        }, {
            'name': 'place_id',
            'required': False,
            'type': 'text',
        }]
