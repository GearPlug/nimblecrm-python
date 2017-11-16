from apps.gp.controllers.base import BaseController
from apps.gp.models import Webhook, StoredData
from django.conf import settings
from django.http import HttpResponse
from django.urls import reverse
import time


class WebhookController(BaseController):
    def __init__(self, connection=None, plug=None, **kwargs):
        super(WebhookController, self).__init__(connection=connection, plug=plug, **kwargs)

    def create_connection(self, connection=None, plug=None, **kwargs):
        super(WebhookController, self).create_connection(connection=connection, plug=plug)

    def test_connection(self):
        return True

    @property
    def has_webhook(self):
        return True

    def create_webhook(self, **kwargs):
        w = Webhook.objects.create(name='webhook', plug=self._plug, url='', expiration='')
        url = settings.WEBHOOK_HOST + reverse('home:webhook', kwargs={'connector': 'webhook', 'webhook_id': w.id})
        w.url = url
        w.save(update_fields=['url', ])

    def do_webhook_process(self, body=None, webhook_id=None, **kwargs):
        webhook = Webhook.objects.get(pk=webhook_id)
        if webhook.plug.gear_source.first().is_active or not webhook.plug.is_tested:
            if not webhook.plug.is_tested:
                webhook.plug.is_tested = False  # TODO CAMBIAR A TRUE
            self.create_connection(connection=webhook.plug.connection, plug=webhook.plug)
            self.download_source_data(body=body)
            return HttpResponse(status=200)
        return HttpResponse(status=400)

    def download_to_stored_data(self, connection_object=None, plug=None, body=None, **kwargs):
        if body is not None and isinstance(body, dict):
            new_data = []
            stamp = str(time.time())
            for k, v in body.items():
                new_data.append(StoredData(name=k, value=v or '', object_id=stamp,
                                           connection=connection_object.connection, plug=plug))
            if new_data:
                result_list = []
                for stored_data in new_data:
                    try:
                        stored_data.save()
                        is_stored = True
                    except Exception as e:
                        is_stored = False
                        break
                result_list.append({'identifier': {'name': 'timestamp', 'value': stored_data.object_id},
                                    'is_stored': is_stored, 'raw': body, })
            return {'downloaded_data': result_list, 'last_source_record': stored_data.object_id}
        return False
