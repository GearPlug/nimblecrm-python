from apps.gp.controllers.base import BaseController
from apps.gp.controllers.exception import ControllerError
import shopify
from django.conf import settings
import re
from apps.gp.models import StoredData
from apps.gp.enum import ConnectorEnum
from apps.gp.map import MapField
from apps.gp.controllers.utils import get_dict_with_source_data

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
        topic_id = self._plug.plug_specification.all()[0].value
        plug_id = self._plug.plug_specification.all()[0].id
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

    def get_target_fields(self, **kwargs):
        return self.get_fields()

    def get_mapping_fields(self, **kwargs):
        fields = self.get_fields()
        return [MapField(f, controller=ConnectorEnum.Shopify) for f in fields]

    def get_fields(self):
        topic_id = self._plug.plug_specification.all()[0].value
        if (topic_id=='customers'):
            return [{"name":"first Name", "required":True, "type":'varchar'},
                    {"name":"last Name","required":False, "type":'varchar'},
                    {"name":"email","required":True, "type": 'varchar'},
                    {"name":"company","required":False, "type": 'varchar'},
                    {"name":"address1", "required":False, "type": 'varchar'},
                    {"name":"address2", "required":False, "type": 'varchar'},
                    {"name":"city","required":False, "type": 'varchar'},
                    {"name":"province","required":False, "type": 'varchar'},
                    {"name":"province code","required":False, "type": 'varchar'},
                    {"name":"country","required":False, "type": 'varchar'},
                    {"name":"country code","requiered":False, "type": 'varchar'},
                    {"name":"zip","required":False, "type": 'varchar'},
                    {"name":"phone","required":True, "type": 'varchar'},
                    {"name":"accepts marketing","required":True, "type": 'varchar', 'values':[True,False]},
                    {"name":"total spent","required":False, "type": 'int'},
                    {"name":"total orders","required":False, "type": 'int'},
                    {"name":"tags","required":False, "type": 'varchar'},
                    {"name":"note","required":False, "type": 'varchar'},
                    {"name":"tax exempt","required":False, "type": 'int'},
                   ]
        if (topic_id=='products'):
            return [{"name":"email", "required":True, "type":'varchar'},
                    {"name":"accepts_marketing","required":False, "type":'varchar'},
                    {"name":"first_name","required":True, "type": 'varchar'},
                    {"name":"last_name","required":False, "type": 'varchar'},
                    {"name":"orders_count", "required":False, "type": 'varchar'},
                    {"name":"note", "required":False, "type": 'varchar'},
                    {"name":"verified_email","required":False, "type": 'varchar'},
                    {"name":"multipass_identifier","required":False, "type": 'varchar'},
                    {"name":"tax_exempt","required":False, "type": 'varchar'},
                    {"name":"phone","required":True, "type": 'varchar'},
                    {"name":"tags","requiered":False, "type": 'varchar'},
                    {"name":"last_order_name","required":False, "type": 'varchar'},
                   ]

    def send_stored_data(self, source_data, target_fields, is_first=False):
        data_list = get_dict_with_source_data(source_data, target_fields)
        if self._plug is not None:
            obj_list = []
            topic_id = self._plug.plug_specification.all()[0].value
            extra = {'controller': 'shopify'}
            for item in data_list:
                try:
                    if (topic_id=="customers"):
                        response=self.insert_customers(data=data_list[0])
                    if response is True:
                        print("item creado")
                        list = shopify.Customer.find()
                        id = list[-1]
                        id = re.findall(r'\d+', str(id))
                        extra['status'] = 's'
                        self._log.info('Item: %s successfully sent.' % (id), extra=extra)
                        obj_list.append(id)
                except Exception as e:
                    print(e)
                    extra['status'] = 'f'
                    self._log.info('Item: failed to send.', extra=extra)
                    return obj_list
        raise ControllerError("There's no plug")

    def get_mapping_fields(self):
        fields = self.get_fields()
        return [MapField(f, controller=ConnectorEnum.Shopify) for f in fields]

    def insert_customers(self, data):  # Metodo para crear un nuevo producto
        fields=self.get_fields()
        values={}
        for i in fields:
            find=False
            for d in data:
                if (i['name']==d):
                    values[i['name']]=data[d]
                    find=True
            if find is False:
                values[i['name']]=''
        session = shopify.Session("https://" + settings.SHOPIFY_SHOP_URL + ".myshopify.com", self._token)
        shopify.ShopifyResource.activate_session(session)
        new_customer = shopify.Customer()
        new_customer.first_name = values["first Name"]
        new_customer.last_name = values["last Name"]
        new_customer.email = values["email"]
        #new_customer.company = "compania"
        sucess=new_customer.save()
        return sucess
        # new_customer.address1 = values["address1"]
        # new_customer.address2 = values["address2"]
        # new_customer.city = values["city"]
        # new_customer.province = values["province"]
        # new_customer.province_code= values["province code"]
        # new_customer.country = values["country"]
        # new_customer.country_code = values["country code"]
        # new_customer.zip = values["zip"]
        # new_customer.phone = values["phone"]
        # new_customer.accepts_marketing = values["accepts marketing"]
        # new_customer.total_spent = values["total spent"]
        # new_customer.total_orders = values["total orders"]
        # new_customer.tags = values["tags"]
        # new_customer.note = values["note"]
        # new_customer.tax_exempt = values["tax exempt"]
        # if new_customer.error:
        #     print(new_customer.error)
        # return None