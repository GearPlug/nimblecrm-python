from django.http import HttpResponse
from django.core.urlresolvers import reverse
from apps.gp.controllers.base import BaseController, GoogleBaseController
from apps.gp.controllers.exception import ControllerError
from apps.gp.controllers.utils import get_dict_with_source_data
from django.conf import settings
from apps.gp.models import StoredData, ActionSpecification, PlugActionSpecification, Webhook
from instagram.client import InstagramAPI
from apps.gp.enum import ConnectorEnum
from apps.gp.map import MapField
from apiclient import discovery, errors, http
from oauth2client import client as GoogleClient
from http import client as httplib
import datetime
import httplib2
import json
import tweepy
import requests
import random
import time
import xmltodict
import os


class TwitterController(BaseController):
    _token = None
    _token_secret = None
    _api = None

    def __init__(self, connection=None, plug=None, **kwargs):
        BaseController.__init__(self, connection=connection, plug=plug, **kwargs)

    def create_connection(self, connection=None, plug=None, **kwargs):
        super(TwitterController, self).create_connection(connection=connection, plug=plug)
        if self._connection_object is not None:
            try:
                self._token = self._connection_object.token
                self._token_secret = self._connection_object.token_secret
            except Exception as e:
                raise ControllerError(
                    code=1001,
                    controller=ConnectorEnum.Twitter,
                    message='The attributes necessary to make the connection were not obtained. {}'.format(str(e)))
        else:
            raise ControllerError(code=1002, controller=ConnectorEnum.Twitter,
                                  message='The controller is not instantiated correctly.')

        try:
            self._api = tweepy.API(self.get_twitter_auth())
        except Exception as e:
            raise ControllerError(code=1003, controller=ConnectorEnum.Twitter,
                                  message='Error in the instantiation of the client. {}'.format(str(e)))
    # api deberia ir en el test connection
    def test_connection(self):
        try:
            response = self._api.me()
        except Exception as e:
            # raise ControllerError(code=1004, controller=ConnectorEnum.Twitter,
            #                       message='Error in the connection test.. {}'.format(str(e)))
            return False
        if response is not None and isinstance(response, dict) and "id" in response:
            return True
        else:
            # raise ControllerError(code=1004, controller=ConnectorEnum.Twitter,
            #                       message='Error in the connection test {}'.format(str(e)))
            return False

    def send_stored_data(self, data_list, **kwargs):
        obj_list = []
        for item in data_list:
            obj_result = {'data': dict(item)}
            try:
                res = self.post_tweet(item)
                obj_result['response'] = res
                obj_result['sent'] = True
                obj_result['identifier'] = res.id
            except Exception as e:
                obj_result['response'] = str(e)
                obj_result['sent'] = False
                obj_result['identifier'] = '-1'

            obj_list.append(obj_result)
        return obj_list

    def get_twitter_auth(self):
        consumer_key = settings.TWITTER_CLIENT_ID
        consumer_secret = settings.TWITTER_CLIENT_SECRET
        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(self._token, self._token_secret)
        return auth

    def post_tweet(self, item):
        api = tweepy.API(self.get_twitter_auth())
        return api.update_status(**item)

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
        fields = self.get_target_fields()
        return [MapField(f, controller=ConnectorEnum.Twitter) for f in fields]


class InstagramController(BaseController):
    _client = None
    TOKEN = 'GearPlug2017'

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

    def test_connection(self, *args, **kwargs):
        return self._client is not None

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
            'callback_url': '%s/wizard/instagram/webhook/event/' % settings.WEBHOOK_HOST
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

    def get_action_specification_options(self, action_specification_id):
        action_specification = ActionSpecification.objects.get(pk=action_specification_id)
        if action_specification.name.lower() == 'account':
            return tuple({'id': a[0], 'name': a[1]} for a in self.get_account())
        else:
            raise ControllerError("That specification doesn't belong to an action in this connector.")

    def do_webhook_process(self, body=None, post=None, force_update=False, **kwargs):
        if body[0]['changed_aspect'] == 'media':
            media_id = body[0]['data']['media_id']
            object_id = body[0]['object_id']
            instagram_list = PlugActionSpecification.objects.filter(
                action_specification__action__action_type='source',
                action_specification__action__connector__name__iexact="instagram",
                value=object_id,
                plug__source_gear__is_active=True)
            for instagram in instagram_list:
                self._connection_object, self._plug = instagram.plug.connection.related_connection, instagram.plug
                if self.test_connection():
                    media = self.get_media(media_id)
                    self.download_source_data(media=media)
        return HttpResponse(status=200)

    @property
    def has_webhook(self):
        return True


class YouTubeController(GoogleBaseController):
    _credential = None
    _client = None
    TOKEN = 'GearPlug2017'
    LEASE_SECONDS = 60 * 60 * 24 * 30

    # Explicitly tell the underlying HTTP transport library not to retry, since
    # we are handling retry logic ourselves.
    httplib2.RETRIES = 1

    # Maximum number of times to retry before giving up.
    MAX_RETRIES = 10

    # Always retry when these exceptions are raised.
    RETRIABLE_EXCEPTIONS = (
        httplib2.HttpLib2Error, IOError, httplib.NotConnected, httplib.IncompleteRead, httplib.ImproperConnectionState,
        httplib.CannotSendRequest, httplib.CannotSendHeader, httplib.ResponseNotReady, httplib.BadStatusLine
    )

    # Always retry when an apiclient.errors.HttpError with one of these status
    # codes is raised.
    RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

    def __init__(self, connection=None, plug=None, **kwargs):
        super(YouTubeController, self).__init__(connection=connection, plug=plug, **kwargs)

    def create_connection(self, connection=None, plug=None, **kwargs):
        super(YouTubeController, self).create_connection(connection=connection, plug=plug)
        if self._connection_object is not None:
            try:
                credentials_json = self._connection_object.credentials_json
            except AttributeError as e:
                raise ControllerError(code=1, controller=ConnectorEnum.YouTube,
                                      message='Error getting the YouTube attributes args. {}'.format(str(e)))
            if credentials_json is not None:
                try:
                    if isinstance(credentials_json, dict):
                        self._credential = GoogleClient.OAuth2Credentials.from_json(json.dumps(credentials_json))
                    else:
                        self._credential = GoogleClient.OAuth2Credentials.from_json(credentials_json)
                except ValueError:
                    raise

                try:
                    self._refresh_token()
                    http_auth = self._credential.authorize(httplib2.Http())
                    self._client = discovery.build('youtube', 'v3', http=http_auth)
                except GoogleClient.HttpAccessTokenRefreshError:
                    self._report_broken_token()

    def test_connection(self):
        params = {
            'mine': True,
            'part': "id,snippet"
        }
        return True if self._client.channels().list(**params).execute() else False

    def download_to_stored_data(self, connection_object, plug, video=None, last_source_record=None, **kwargs):
        if video is None:
            return False
        new_data = []
        video = video['items'][0]
        video_id = video['id']
        q = StoredData.objects.filter(connection=connection_object.connection, plug=plug, object_id=video_id)
        if not q.exists():
            for k, v in video['snippet'].items():
                obj = StoredData(connection=connection_object.connection, plug=plug, object_id=video_id, name=k,
                                 value=v or '')
                new_data.append(obj)
        is_stored = False
        for item in new_data:
            try:
                item.save()
                is_stored = True
            except Exception as e:
                print(e)
        result_list = [{'raw': video, 'is_stored': is_stored, 'identifier': {'name': 'id', 'value': video_id}}]
        return {'downloaded_data': result_list, 'last_source_record': video_id}

    def send_stored_data(self, data_list, is_first=False):
        # if is_first and data_list:
        #     try:
        #         data_list = [data_list[-1]]
        #     except:
        #         data_list = []
        # if self._plug is not None:
        #     for obj in data_list:
        #         self.initialize_upload(obj)
        #     extra = {'controller': 'youtube'}
        raise ControllerError("Incomplete.")

    def create_webhook(self):
        # Creacion de Webhook
        webhook = Webhook.objects.create(name='youtube', plug=self._plug, url='', expiration='')
        # Verificar host para determinar url_base
        url_base = settings.WEBHOOK_HOST
        url_path = reverse('home:webhook', kwargs={'connector': 'youtube', 'webhook_id': webhook.id})
        url = url_base + url_path

        subscribe_url = 'https://pubsubhubbub.appspot.com/subscribe'
        topic_url = 'https://www.youtube.com/xml/feeds/videos.xml?channel_id='

        params = {
            'hub.mode': 'subscribe',
            'hub.callback': url,
            'hub.lease_seconds': self.LEASE_SECONDS,
            'hub.topic': topic_url + self._plug.plug_action_specification.first().value,
            'hub.verify_token': self.TOKEN
        }

        response = requests.post(url=subscribe_url, data=params)

        if response.status_code == 202:
            webhook.url = url_base + url_path
            webhook.is_active = True
            webhook.expiration = (datetime.datetime.now() + datetime.timedelta(seconds=self.LEASE_SECONDS)).timestamp()
            webhook.save(update_fields=['url', 'generated_id', 'is_active', 'expiration'])
            return True
        else:
            webhook.is_deleted = True
            webhook.save(update_fields=['is_deleted', ])
            return False

    def delete_webhook(self, webhook):
        # Verificar host para determinar url_base
        url_base = settings.WEBHOOK_HOST
        url_path = reverse('home:webhook', kwargs={'connector': 'youtube', 'webhook_id': webhook.id})
        url = url_base + url_path

        subscribe_url = 'https://pubsubhubbub.appspot.com/subscribe'
        topic_url = 'https://www.youtube.com/xml/feeds/videos.xml?channel_id='

        params = {
            'hub.mode': 'unsubscribe',
            'hub.callback': url,
            'hub.lease_seconds': self.LEASE_SECONDS,
            'hub.topic': topic_url + self._plug.plug_action_specification.first().value,
            'hub.verify_token': self.TOKEN
        }

        return requests.post(url=subscribe_url, data=params)

    def do_webhook_process(self, body=None, POST=None, webhook_id=None, **kwargs):
        root = xmltodict.parse(body)
        entry = root['feed']['entry']
        channel_id = entry['yt:channelId']
        video_id = entry['yt:videoId']
        webhook = Webhook.objects.get(pk=webhook_id)

        if webhook.plug.gear_source.first().is_active or not webhook.plug.is_tested:
            if not webhook.plug.is_tested:
                webhook.plug.is_tested = True
            self.create_connection(connection=webhook.plug.connection.related_connection, plug=webhook.plug)
            if self.test_connection():
                video = self.get_video(video_id)
                self.download_source_data(video=video)
                webhook.plug.save()
        return HttpResponse(status=200)

    def get_channel_list(self):
        params = {
            'mine': True,
            'part': "id,snippet"
        }
        response = self._client.channels().list(**params).execute()
        return response['items']

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

    def get_action_specification_options(self, action_specification_id):
        action_specification = ActionSpecification.objects.get(pk=action_specification_id)
        if action_specification.name.lower() in ['channel']:
            _tuple = tuple({'id': p['id'], 'name': p['snippet']['title']} for p in self.get_channel_list())
            return _tuple
        else:
            raise ControllerError("That specification doesn't belong to an action in this connector.")

    @property
    def has_webhook(self):
        return True
