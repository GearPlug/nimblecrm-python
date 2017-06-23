from apps.gp.controllers.base import BaseController
from apps.gp.controllers.exception import ControllerError
import shopify
from django.conf import settings
import re
from apps.gp.models import StoredData
from apps.gp.enum import ConnectorEnum
from apps.gp.map import MapField

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
        return [{'name':'customers', 'id':'customers'},{'name':'products', 'id':'products'}]

    def download_to_stored_data(self, connection_object, plug, list=None):
        if plug is None:
            plug = self._plug
        topic_id = self._plug.plug_specification.all()[0].value
        # print("lista webhooks")
        # webhook=self.get_list_webhooks()
        # print(webhook)

        if list is None:
            session = shopify.Session("https://" + settings.SHOPIFY_SHOP_URL + ".myshopify.com", self._token)
            shopify.ShopifyResource.activate_session(session)
            if (topic_id=="customers"):list=shopify.Customer.find()
            elif (topic_id=="products"): list=shopify.Products.find()

        new_data = []
        for item in list:
            m = re.findall(r'\d+', str(item))
            id = int(m[0])
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug, object_id=id)
            if not q.exists():
                if (topic_id == "customers"):details = shopify.Customer.find(id)
                elif (topic_id == "products"):details = shopify.Products.find(id)
                for value in details.attributes:
                    information=details.attributes[value]
                    if (information==None):
                        information=''
                    new_data.append(StoredData(name=value, value=information, object_id=id,
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
        print("primero")
        topic_id = self._plug.plug_specification.all()[0].value
        plug_id = self._plug.plug_specification.all()[0].id
        print("plug_id")
        print(plug_id)
        session = shopify.Session("https://" + settings.SHOPIFY_SHOP_URL + ".myshopify.com", self._token)
        shopify.ShopifyResource.activate_session(session)
        new_webhook = shopify.Webhook()
        new_webhook.topic = topic_id+"/create"
        new_webhook.address =  "https://l.grplug.com/wizard/shopify/webhook/event/%s/" % (plug_id)
        new_webhook.format = "json"
        success = new_webhook.save()
        if success == True:
            print("Se creo el webhook shopify")
            return True
        return False

    def get_list_webhooks(self):  #Metodo para listar los webhooks
        session = shopify.Session("https://" + settings.SHOPIFY_SHOP_URL+ ".myshopify.com", self._token)
        shopify.ShopifyResource.activate_session(session)
        webhook = shopify.Webhook.find()
        return webhook

    def get_target_fields(self, module, **kwargs):
        return self.get_fields()

    def get_mapping_fields(self, **kwargs):
        fields = self.get_fields()
        return [MapField(f, controller=ConnectorEnum.Shopify) for f in fields]

    def get_fields(self):
        topic_id = self._plug.plug_specification.all()[0].value
        if (topic_id=='customers'):
            return [{"name":"email", "required":True},
                    {"name":"accepts_marketing","required":False},
                    {"name":"first_name","required":True},
                    {"name":"last_name","required":False},
                    {"name":"orders_count", "required":False},
                    {"name":"note", "required":False},
                    {"name":"verified_email","required":False},
                    {"name":"multipass_identifier","required":False},
                    {"name":"tax_exempt","required":False},
                    {"name":"phone","required":True},
                    {"name":"tags","requiered":False},
                    {"name":"last_order_name","required":False},
                   ]



