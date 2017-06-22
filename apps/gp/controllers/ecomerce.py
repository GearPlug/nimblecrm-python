from apps.gp.controllers.base import BaseController
from apps.gp.controllers.exception import ControllerError
import shopify
from django.conf import settings
import re
from apps.gp.models import StoredData

class EbayController(BaseController):
    pass


class MercadoLibreController(BaseController):
    pass


class AmazonSellerCentralController(BaseController):
    pass


class PayUController(BaseController):
    pass

class ShopifyController(BaseController):
    _token = None

    def __init__(self, *args, **kwargs):
        BaseController.__init__(self, *args, **kwargs)

    def create_connection(self, *args, **kwargs):
        if args:
            super(ShopifyController, self).create_connection(*args)
            if self._connection_object is not None:
                try:
                    self._token = self._connection_object.token
                except Exception as e:
                    print("Error getting the shopify token")
                    print(e)
        elif kwargs:
            host = kwargs.pop('token', None)
        return self._token is not None

    def get_topics(self):
        return [{'name':'Customers', 'id':'Customers'},{'name':'Products', 'id':'Products'}]

    def download_to_stored_data(self, connection_object, plug):
        if plug is None:
            plug = self._plug
        topic_id = self._plug.plug_specification.all()[0].value
        session = shopify.Session("https://" + settings.SHOPIFY_SHOP_URL + ".myshopify.com", self._token)
        shopify.ShopifyResource.activate_session(session)
        if (topic_id=="Customers"):list=shopify.Customer.find()
        elif (topic_id=="Products"): list=shopify.Products.find()
        new_data = []
        for item in list:
            m = re.findall(r'\d+', str(item))
            id = int(m[0])
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug, object_id=id)
            if not q.exists():
                if (topic_id == "Customers"):details = shopify.Customer.find(id)
                elif (topic_id == "Products"):details = shopify.Products.find(id)
                print("details")
                print(details.attributes)
                print(type(details.attributes))
                for value in details.attributes:
                    new_data.append(StoredData(name=value, value=details.attributes[value], object_id=id,
                                                   connection=connection_object.connection, plug=plug))
        if new_data:
            extra = {'controller': 'shopify'}
            for item in new_data:
                try:
                    self._log.info('Item ID: %s, Connection: %s, Plug: %s successfully stored.' % (
                        item.object_id, item.plug.id, item.connection.id), extra=extra)
                    item.save()
                except:
                    extra['status'] = 'f'
                    self._log.info('Item ID: %s, Field: %s, Connection: %s, Plug: %s failed to save.' % (
                        item.object_id, item.name, item.plug.id, item.connection.id), extra=extra)
        return True

    def create_webhook(self):
        topic_id = self._plug.plug_specification.all()[0].value
        plug_id = self._plug.plug_specification.all()[0].id
        print("plug_id")
        print(plug_id)
        new_webhook = shopify.Webhook()
        new_webhook.topic = topic_id+"/create"
        new_webhook.address =  "https://l.grplug.com/wizard/shopify/webhook/event/%s/" % (plug_id)
        new_webhook.format = "json"
        success = new_webhook.save()
        print(success)

        # if r.status_code == 201:
        #     print("Se creo el webhook survey monkey")
        #     return True
        return False





