from apps.gp.controllers.base import BaseController
from apps.gp.controllers.exception import ControllerError
from apps.gp.controllers.utils import get_dict_with_source_data
from django.conf import settings
from apps.gp.models import StoredData
from instagram.client import InstagramAPI
import tweepy
import requests


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


class InstagramController(BaseController):
    _client = None

    def __init__(self, *args, **kwargs):
        BaseController.__init__(self, *args, **kwargs)

    def create_connection(self, *args, **kwargs):
        token = None
        if args:
            super(InstagramController, self).create_connection(*args)
            if self._connection_object is not None:
                try:
                    token = self._connection_object.token
                except Exception as e:
                    print("Error getting the Instagram Token")
                    print(e)
        elif kwargs:
            if 'token' in kwargs:
                token = kwargs['token']
        me = None
        if token:
            self._client = InstagramAPI(access_token=token, client_secret=settings.INSTAGRAM_CLIENT_SECRET)
            me = self._client.user()
        return me is not None

    def download_to_stored_data(self, connection_object=None, plug=None, media=None, **kwargs):
        if media is not None:
            _items = []
            # media es un objecto, se debe convertir a diccionario:
            _dict = media.__dict__
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug,
                                          object_id=media.id)
            if not q.exists():
                for k, v in _dict.items():
                    obj = StoredData(connection=connection_object.connection, plug=plug,
                                     object_id=media.id, name=k, value=v or '')
                    _items.append(obj)
            extra = {}
            for item in _items:
                extra['status'] = 's'
                extra = {'controller': 'instagram'}
                self._log.info('Item ID: %s, Connection: %s, Plug: %s successfully stored.' % (
                    item.object_id, item.plug.id, item.connection.id), extra=extra)
                item.save()
        return False

    def create_webhook(self):
        url = 'https://api.instagram.com/v1/subscriptions/'
        body = {
            'client_id': settings.INSTAGRAM_CLIENT_ID,
            'client_secret': settings.INSTAGRAM_CLIENT_SECRET,
            'object': 'user',
            'aspect': 'media',
            'verify_token': 'GearPlug2017',
            'callback_url': 'http://m.gearplug.com/wizard/instagram/webhook/event/'
        }
        r = requests.post(url, data=body)
        if r.status_code == 201:
            return True
        return False

    def get_account(self):
        user = self._client.user()
        return [(user.id, user.username)]

    def get_media(self, media_id):
        media = self._client.media(media_id)
        return media
