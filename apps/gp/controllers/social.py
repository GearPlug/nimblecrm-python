from apps.gp.controllers.base import BaseController
from apps.gp.controllers.exception import ControllerError
from apps.gp.controllers.utils import get_dict_with_source_data
from django.conf import settings
from apps.gp.models import StoredData
from instagram.client import InstagramAPI
from apps.gp.enum import ConnectorEnum
from apps.gp.map import MapField
from apiclient import discovery, errors, http
from oauth2client import client as GoogleClient
from http import client as httplib
import httplib2
import json
import tweepy
import requests
import random
import time

import os


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

    def test_connection(self):
        return self._token is not None

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

    def get_mapping_fields(self, **kwargs):
        fields=self.get_target_fields()
        return [MapField(f, controller=ConnectorEnum.Twitter) for f in fields]


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


class YouTubeController(BaseController):
    _credential = None
    _client = None

    # Explicitly tell the underlying HTTP transport library not to retry, since
    # we are handling retry logic ourselves.
    httplib2.RETRIES = 1

    # Maximum number of times to retry before giving up.
    MAX_RETRIES = 10

    # Always retry when these exceptions are raised.
    RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, httplib.NotConnected,
                            httplib.IncompleteRead, httplib.ImproperConnectionState,
                            httplib.CannotSendRequest, httplib.CannotSendHeader,
                            httplib.ResponseNotReady, httplib.BadStatusLine)

    # Always retry when an apiclient.errors.HttpError with one of these status
    # codes is raised.
    RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

    def __init__(self, *args, **kwargs):
        BaseController.__init__(self, *args, **kwargs)

    def create_connection(self, *args, **kwargs):
        credentials_json = None
        if args:
            super(YouTubeController, self).create_connection(*args)
            if self._connection_object is not None:
                try:
                    credentials_json = self._connection_object.credentials_json
                except Exception as e:
                    print("Error getting the YouTube Token")
                    print(e)
                    credentials_json = None
            elif not args and kwargs:
                if 'credentials_json' in kwargs:
                    credentials_json = kwargs.pop('credentials_json')
            else:
                credentials_json = None
        me = None
        if credentials_json is not None:
            try:
                _json = json.dumps(credentials_json)
                self._credential = GoogleClient.OAuth2Credentials.from_json(_json)
                print('1')
                self._refresh_token()
                print('2')
                http_auth = self._credential.authorize(httplib2.Http())
                self._client = discovery.build('youtube', 'v3', http=http_auth)
                params = {
                    'mine': True,
                    'part': "id,snippet"
                }
                me = self._client.channels().list(**params).execute()
            except ValueError:
                print("Error getting the YouTube attributes 2")
                self._credential = None
                self._client = None
                me = None
        return me is not None

    def _upate_connection_object_credentials(self):
        self._connection_object.credentials_json = self._credential.to_json()
        self._connection_object.save()

    def _refresh_token(self, token=''):
        if self._credential.access_token_expired:
            self._credential.refresh(httplib2.Http())
            self._upate_connection_object_credentials()

    def download_to_stored_data(self, connection_object=None, plug=None, video=None, **kwargs):
        video = video['items'][0]
        if video is not None:
            _items = []
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug,
                                          object_id=video['id'])
            if not q.exists():
                for k, v in video['snippet'].items():
                    obj = StoredData(connection=connection_object.connection, plug=plug,
                                     object_id=video['id'], name=k, value=v or '')
                    _items.append(obj)
            extra = {}
            for item in _items:
                extra['status'] = 's'
                extra = {'controller': 'youtube'}
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
                self.initialize_upload(obj)
            extra = {'controller': 'youtube'}
        raise ControllerError("Incomplete.")

    def create_webhook(self):
        subscribe_url = 'https://pubsubhubbub.appspot.com/subscribe'
        topic_url = 'https://www.youtube.com/xml/feeds/videos.xml?channel_id='
        callback_url = 'https://m.grplug.com/wizard/youtube/webhook/event/'

        params = {
            'hub.mode': 'subscribe',
            'hub.callback': callback_url,
            'hub.lease_seconds': 60 * 60 * 24 * 365,
            'hub.topic': topic_url + self._plug.plug_action_specification.all()[0].value
        }

        response = requests.post(url=subscribe_url, data=params)

        if response.status_code == 204:
            return True
        return False

    def get_channel_list(self):
        params = {
            'mine': True,
            'part': "id,snippet"
        }
        me = self._client.channels().list(**params).execute()
        return [{'id': i['id'], 'name': i['snippet']['title']} for i in me['items']]

    def get_video(self, video_id):
        params = {
            'id': video_id,
            'part': "id,snippet"
        }
        return self._client.videos().list(**params).execute()

    def initialize_upload(self, obj):
        tags = None
        title = obj.get('title', None)
        description = obj.get('description', None)
        keywords = obj.get('keywords', None)
        category = obj.get('categoryId', None)
        privacy_status = obj.get('privacyStatus', None)
        file = obj.get('file', None)
        if keywords:
            tags = keywords.split(",")

        body = dict(
            snippet=dict(
                title=title,
                description=description,
                tags=tags,
                categoryId=category
            ),
            status=dict(
                privacyStatus=privacy_status
            )
        )

        # Call the API's videos.insert method to create and upload the video.
        insert_request = self._client.videos().insert(
            part=",".join(body.keys()),
            body=body,
            # The chunksize parameter specifies the size of each chunk of data, in
            # bytes, that will be uploaded at a time. Set a higher value for
            # reliable connections as fewer chunks lead to faster uploads. Set a lower
            # value for better recovery on less reliable connections.
            #
            # Setting "chunksize" equal to -1 in the code below means that the entire
            # file will be uploaded in a single HTTP request. (If the upload fails,
            # it will still be retried where it left off.) This is usually a best
            # practice, but if you're using Python older than 2.6 or if you're
            # running on App Engine, you should set the chunksize to something like
            # 1024 * 1024 (1 megabyte).
            media_body=http.MediaFileUpload(file, chunksize=-1, resumable=True)
        )

        self.resumable_upload(insert_request)

    # This method implements an exponential backoff strategy to resume a
    # failed upload.
    def resumable_upload(self, insert_request):
        response = None
        error = None
        retry = 0
        while response is None:
            try:
                print("Uploading file...")
                status, response = insert_request.next_chunk()
                if 'id' in response:
                    print("Video id '%s' was successfully uploaded." % response['id'])
                else:
                    print("The upload failed with an unexpected response: %s" % response)
            except errors.HttpError as e:
                if e.resp.status in self.RETRIABLE_STATUS_CODES:
                    error = "A retriable HTTP error %d occurred:\n%s" % (e.resp.status, e.content)
                else:
                    raise
            except self.RETRIABLE_EXCEPTIONS as e:
                error = "A retriable error occurred: %s" % e

            if error is not None:
                print(error)
                retry += 1
                if retry > self.MAX_RETRIES:
                    print("No longer attempting to retry.")

                max_sleep = 2 ** retry
                sleep_seconds = random.random() * max_sleep
                print("Sleeping %f seconds and then retrying..." % sleep_seconds)
                time.sleep(sleep_seconds)

    def get_target_fields(self, **kwargs):
        return [{
            'name': 'title',
            'required': True,
            'type': 'text',
        }, {
            'name': 'description',
            'required': False,
            'type': 'text',
        }, {
            'name': 'category',
            'required': False,
            'type': 'choices',
            'values': [c['snippet']['title'] for c in self.get_video_categories()]
        }, {
            'name': 'privacyStatus',
            'required': False,
            'type': 'choices',
            'values': ['public', 'private', 'unlisted']
        }, {
            'name': 'keywords',
            'required': False,
            'type': 'text',
        }, {
            'name': 'file',
            'required': True,
            'type': 'text',
        }]

    def get_video_categories(self, region_code='US'):
        params = {
            'regionCode': region_code,
            'part': "id,snippet"
        }
        categories = self._client.videoCategories().list(**params).execute()
        return categories['items']

    def get_mapping_fields(self, **kwargs):
        fields = self.get_target_fields()
        return [MapField(f, controller=ConnectorEnum.YouTube) for f in fields]