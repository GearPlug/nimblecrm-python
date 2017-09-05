import ast
from apps.gp.controllers.base import BaseController
from apps.gp.controllers.exception import ControllerError
import shopify
from django.conf import settings
from django.shortcuts import HttpResponse
import re
from apps.gp.models import StoredData, ActionSpecification, Action, Plug, Webhook
from apps.gp.enum import ConnectorEnum
from apps.gp.map import MapField
from apps.gp.controllers.utils import get_dict_with_source_data
from magento import MagentoAPI
import json
import ast
from django.urls import reverse
from mercadolibre.client import Client as MercadolibreClient


class EbayController(BaseController):
    pass


class MercadoLibreController(BaseController):
    _token = None
    _site = None
    _client = None

    def __init__(self, *args, **kwargs):
        BaseController.__init__(self, *args, **kwargs)

    def create_connection(self, *args, **kwargs):
        if args:
            super(MercadoLibreController, self).create_connection(*args)
            if self._connection_object is not None:
                try:
                    self._token = self._connection_object.token
                    self._site = self._connection_object.site
                except Exception as e:
                    print("Error getting the mercadolibre token")
            else:
                raise ControllerError('No connection.')
        try:
            self._client = MercadolibreClient(client_id=settings.MERCADOLIBRE_CLIENT_ID,
                                              client_secret=settings.MERCADOLIBRE_CLIENT_SECRET, site=self._site)
            self._client.set_token(ast.literal_eval(self._token))
        except Exception:
            raise ControllerError('No connection.')

    def test_connection(self):
        return self.get_me() is not None

    def send_stored_data(self, source_data, target_fields, is_first=False):
        obj_list = []
        data_list = get_dict_with_source_data(source_data, target_fields)
        if is_first:
            if data_list:
                try:
                    data_list = [data_list[-1]]
                except:
                    data_list = []
        if self._plug is not None:
            extra = {'controller': 'mercadolibre'}
            for obj in data_list:
                res = self.list_product(obj)
            return
        raise ControllerError("Incomplete.")

    def list_product(self, obj):
        result = self._client.list_item(**obj)
        return result

    def get_target_fields(self, **kwargs):
        return self.get_fields()

    def get_mapping_fields(self, **kwargs):
        fields = self.get_fields()
        return [MapField(f, controller=ConnectorEnum.MercadoLibre) for f in fields]

    def get_fields(self):
        return [
            {
                'name': 'title',
                'required': True,
                'type': 'text'
            }, {
                'name': 'category_id',
                'required': True,
                'type': 'text'
            }, {
                'name': 'price',
                'required': True,
                'type': 'text'
            }, {
                'name': 'currency_id',
                'required': True,
                'type': 'text'
            }, {
                'name': 'available_quantity',
                'required': True,
                'type': 'text'
            }, {
                'name': 'buying_mode',
                'required': True,
                'type': 'choices',
                'values': ['buy_it_now']
            }, {
                'name': 'listing_type_id',
                'required': True,
                'type': 'choices',
                'values': [l['id'] for l in self.get_listing_types()]
            }, {
                'name': 'condition',
                'required': True,
                'type': 'choices',
                'values': ['new', 'used', 'not_specified']
            }, {
                'name': 'description',
                'required': False,
                'type': 'text'
            }, {
                'name': 'video_id',
                'required': False,
                'type': 'text'
            }, {
                'name': 'warranty',
                'required': True,
                'type': 'text'
            }, {
                'name': 'pictures',
                'required': False,
                'type': 'text'
            },

        ]

    def get_me(self):
        return self._client.me()

    def get_sites(self):
        return self._client.get_sites()

    def get_categories(self):
        # No se está utilizando porque no hay forma de saber cuales categorías son "hojas"
        return self._client.get_categories(self._site)

    def get_listing_types(self):
        l = self._client.get_listing_types(self._site)
        return l

    def do_webhook_process(self, body=None, post=None, force_update=False, **kwargs):
        plugs = Plug.objects.filter(
            action__action_type='source',
            action__connector__name__iexact='mercadolibre',
            action__name=body['topic'],
            connection__connection_mercadolibre__user_id=body['user_id'])
        for plug in plugs:
            self._connection_object, self._plug = plug.connection.related_connection, plug
            self.create_connection(self._connection_object, self._plug)
            if self.test_connection():
                self.download_source_data(event=body)
        return HttpResponse(status=200)

    def download_to_stored_data(self, connection_object=None, plug=None, event=None, **kwargs):
        if event is not None:
            _items = []
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug,
                                          object_id=None)
            if not q.exists():
                for k, v in event.items():
                    obj = StoredData(connection=connection_object.connection, plug=plug,
                                     object_id=None, name=k, value=v or '')
                    _items.append(obj)
            extra = {}
            for item in _items:
                extra['status'] = 's'
                extra = {'controller': 'mercadolibre'}
                self._log.info('Item ID: %s, Connection: %s, Plug: %s successfully stored.' % (
                    item.object_id, item.plug.id, item.connection.id), extra=extra)
                item.save()
        return False


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
                    self._shop_url = self._connection_object.shop_url
                except Exception as e:
                    print("Error getting the shopify token")

    def test_connection(self):
        try:
            session = shopify.Session("https://" + self._shop_url, self._token)
            return self._token and self._shop_url is not None
        except:
            raise ControllerError("TODO")

    def download_to_stored_data(self, connection_object, plug, list=None):
        if plug is None:
            plug = self._plug
        action = plug.action.name
        session = shopify.Session("https://" + self._shop_url, self._token)
        shopify.ShopifyResource.activate_session(session)

        if list is None:
            list = []
            if action == 'new customer':
                list2 = shopify.Customer.find()
            elif action == 'new product':
                list2 = shopify.Product.find()
            elif action == 'new order':
                list2 = shopify.Order.find()
            for l in list2:
                m = re.findall(r'\d+', str(l))
                list.append(m[0])

        new_data = []
        for item in list:
            id_field = int(item)
            print("item", item, type(item))
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug, object_id=id_field)
            if not q.exists():
                if action == 'new customer':
                    details = shopify.Customer.find(id_field)
                elif action == 'new product':
                    details = shopify.Product.find(id_field)
                elif action == 'new order':
                    details = shopify.Order.find(id_field)
                for value in details.attributes:
                    information = details.attributes[value] or ''
                    new_data.append(StoredData(name=value, value=information, object_id=id_field,
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
        action = self._plug.action.name
        webhook = Webhook.objects.create(name='shopify', plug=self._plug, url='')
        url_path = reverse('home:webhook', kwargs={'connector': 'shopify', 'webhook_id': webhook.id})
        session = shopify.Session("https://" + self._shop_url, self._token)
        url_base = settings.CURRENT_HOST
        if action == 'new product':
            topic = 'products'
        elif action == 'new customer':
            topic = 'customers'
        elif action == 'new order':
            topic = 'orders'
        new_webhook = shopify.Webhook()
        new_webhook.topic = topic + "/create"
        new_webhook.address = url_base + url_path
        new_webhook.format = "json"
        success = new_webhook.save()
        shopify.ShopifyResource.activate_session(session)
        if success == True:
            webhook.url = url_base + url_path
            webhook.is_active = True
            id = re.findall(r'\d+', str(self.get_list_webhooks()[-1]))
            webhook.generated_id = id[0]
            webhook.save(update_fields=['url', 'generated_id', 'is_active'])
            print("Se creo el webhook shopify")
            return True
        else:
            webhook.is_deleted = True
            webhook.save(update_fields=['is_deleted', ])
            print("Error al crear el webhook en shopify")
        return False

    def get_list_webhooks(self):  # Metodo para listar los webhooks
        session = shopify.Session("https://" + self._shop_url, self._token)
        shopify.ShopifyResource.activate_session(session)
        webhook = shopify.Webhook.find()
        print(webhook)
        return webhook

    def get_target_fields(self, **kwargs):
        return self.get_fields()

    def get_mapping_fields(self, **kwargs):
        fields = self.get_fields()
        return [MapField(f, controller=ConnectorEnum.Shopify) for f in fields]

    def get_fields(self):
        topic_id = self._plug.plug_action_specification.all()[0].value
        if (topic_id == 'customers'):
            return [{"name": "first Name", "required": True, "type": 'varchar'},
                    {"name": "last Name", "required": False, "type": 'varchar'},
                    {"name": "email", "required": True, "type": 'varchar'},
                    {"name": "address1", "required": False, "type": 'varchar'},
                    {"name": "city", "required": False, "type": 'varchar'},
                    {"name": "country", "required": False, "type": 'varchar'},
                    {"name": "zip", "required": False, "type": 'varchar'},
                    {"name": "phone", "required": True, "type": 'varchar'},
                    ]
        if (topic_id == 'products'):
            return [{"name": "title", "required": True, "type": 'varchar'},
                    {"name": "type", "required": False, "type": 'varchar'},
                    {"name": "vendor", "required": False, "type": 'varchar'},
                    ]

    def send_stored_data(self, source_data, target_fields, is_first=False):
        data_list = get_dict_with_source_data(source_data, target_fields)
        if self._plug is not None:
            obj_list = []
            topic_id = self._plug.plug_action_specification.all()[0].value
            extra = {'controller': 'shopify'}
            for item in data_list:
                try:
                    if (topic_id == "customers"):
                        response = self.create_customers(data=item)
                    if (topic_id == "products"):
                        response = self.create_product(data=item)
                    if response is True:
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

    def create_customers(self, data):
        values = self.get_values(data)
        session = shopify.Session("https://" + settings.SHOPIFY_SHOP_URL + ".myshopify.com", self._token)
        shopify.ShopifyResource.activate_session(session)
        new_customer = shopify.Customer()
        new_customer.first_name = values["first Name"]
        new_customer.last_name = values["last Name"]
        new_customer.email = values["email"]
        new_customer.addresses = [{"address1": values["address1"], "city": values["city"], "phone": values["phone"]}]
        sucess = new_customer.save()
        return sucess

    def create_product(self, data):
        values = self.get_values(data)
        session = shopify.Session("https://" + settings.SHOPIFY_SHOP_URL + ".myshopify.com", self._token)
        shopify.ShopifyResource.activate_session(session)
        new_product = shopify.Product()
        new_product.title = values['title']
        new_product.type = values['type']
        new_product.vendor = values['vendor']
        return new_product.save()

    def get_values(self, data):
        fields = self.get_fields()
        values = {}
        for i in fields:
            find = False
            for d in data:
                if (i['name'] == d):
                    values[i['name']] = data[d]
                    find = True
            if find is False: values[i['name']] = ""
        return values


class MagentoController(BaseController):
    _connection = None
    _host = None
    _port = None
    _connection_user = None
    _connection_password = None

    def __init__(self, *args, **kwargs):
        super(MagentoController, self).__init__(*args, **kwargs)

    def create_connection(self, *args, **kwargs):
        if args:
            super(MagentoController, self).create_connection(*args)
            if self._connection_object is not None:
                host = self._connection_object.host
                port = self._connection_object.port
                user = self._connection_object.connection_user
                password = self._connection_object.connection_password
                try:
                    self._connection = MagentoAPI(host=host, port=port, api_user=user, api_key=password)
                except Exception as e:
                    print("Error create connection Magento")
                    print(e)
                    self._connection is None

    def test_connection(self):
        return self._connection is not None

    def get_options(self):
        return [{'name': 'orders', 'id': 'orders'}, {'name': 'products', 'id': 'products'},
                {'name': 'customers', 'id': 'customers'}]

    def get_action_specification_options(self, action_specification_id):
        action_specification = ActionSpecification.objects.get(pk=action_specification_id)
        type = Action.objects.get(pk=action_specification.action_id)
        options = []
        if action_specification.name.lower() == 'field':
            for o in self.get_options():
                if (type.action_type == "target" and o['id'] == "orders"):
                    pass
                else:
                    options.append({'name': o['name'], 'id': o['id']})
            return tuple(options)
        else:
            raise ControllerError("That specification doesn't belong to an action in this connector.")

    def download_to_stored_data(self, connection_object, plug):
        if plug is None:
            plug = self._plug
        field_id = self._plug.plug_action_specification.all()[0].value
        magento = self._connection

        if (field_id == "orders"):
            details = magento.sales_order.list()
        elif (field_id == "products"):
            details = magento.catalog_product.list()
        elif (field_id == "customers"):
            details = magento.customer.list()

        new_data = []
        for detail in details:
            id = int(self.get_id(detail, field_id))
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug, object_id=id)
            if not q.exists():
                for k, v in detail.items():
                    if v is None: v = ''
                    new_data.append(StoredData(name=k, value=v, object_id=id,
                                               connection=connection_object.connection, plug=plug))
        if new_data:
            extra = {'controller': 'magento'}
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

    def get_id(self, item, field_id):
        if (field_id == "orders"):
            id = item['order_id']
        elif (field_id == "products"):
            id = item['product_id']
        elif (field_id == "customers"):
            id = item['customer_id']
        return id

    def get_target_fields(self, **kwargs):
        return self.get_fields()

    def get_mapping_fields(self, **kwargs):
        fields = self.get_fields()
        return [MapField(f, controller=ConnectorEnum.Magento) for f in fields]

    def get_fields(self):
        topic_id = self._plug.plug_action_specification.all()[0].value
        if (topic_id == 'customers'):
            group = self._connection.customer_group.list()
            return [{"name": "email", "required": True, "type": "varchar", "label": "Email"},
                    {"name": "firstname", "required": True, "type": "varchar", "label": "First Name"},
                    {"name": "lastname", "required": True, "type": "varchar", "label": "Last Name"},
                    {"name": "group_id", "required": True, "type": "int", "label": "Group", "choices": group},
                    {"name": "prefix", "required": False, "type": "varchar", "label": "Prefix"},
                    {"name": "suffix", "required": False, "type": "varchar", "label": "Suffix"},
                    {"name": "dob", "required": False, "type": "varchar", "label": "Date Of Birth"},
                    {"name": "taxvat", "required": False, "type": "varchar", "label": "Tax/VAT Number"},
                    {"name": "gender", "required": False, "type": "int", "label": "Gender",
                     "choices": [{'id': 1, "name": "Male"}, {"id": 2, "name": "Female"}]},
                    {"name": "middlename", "required": False, "type": "varchar", "label": "Middle Name/Initial"},
                    ]
        if (topic_id == 'products'):
            type = self._connection.catalog_product_type.list()
            attribute = self._connection.catalog_product_attribute_set.list()
            return [
                {"name": "product_type", "required": True, "type": 'varchar', "label": "Product Type", "choices": type},
                {"name": "attribute_set_id", "required": True, "type": 'varchar', "label": "Attribute Set",
                 "choices": attribute},
                {"name": "sku", "required": True, "type": 'varchar', "label": "SKU"},
                {"name": "name", "required": True, "type": 'varchar', "label": "Name"},
                {"name": "description", "required": False, "type": "varchar", "label": "Description"},
                {"name": "short_description", "required": False, "type": "varchar", "label": "Short Description"},
                {"name": "weight", "required": False, "type": "varchar", "label": "Weight"},
                {"name": "url_key", "required": False, "type": "varchar", "label": "URL Key"},
                {"name": "price", "required": False, "type": "varchar", "label": "Price"},
                {"name": "special_price", "required": False, "type": "varchar", "label": "Special Price"},
                {"name": "special_from_date", "required": False, "type": "varchar", "label": "Special Price From Date"},
                {"name": "special_to_date", "required": False, "type": "varchar", "label": "Special Price To Date"},
            ]

    def send_stored_data(self, source_data, target_fields, is_first=False):
        data_list = get_dict_with_source_data(source_data, target_fields)
        if self._plug is not None:
            obj_list = []
            field_id = self._plug.plug_action_specification.all()[0].value
            extra = {'controller': 'magento'}
            for item in data_list:
                try:
                    if (field_id == "customers"):
                        response = self.create_customer(item)
                    if (field_id == "products"):
                        response = self.create_product(item)
                    extra['status'] = 's'
                    self._log.info('Item: %s successfully sent.' % (int(response)), extra=extra)
                    obj_list.append(int(response))
                except Exception as e:
                    print(e)
                    extra['status'] = 'f'
                    self._log.info('Item: failed to send.', extra=extra)
            return obj_list
        raise ControllerError("There's no plug")

    def create_customer(self, item):
        customer = {i: item[i] for i in item}
        data = item["group_id"]
        data = ast.literal_eval(data)
        customer["group_id"] = int(data["customer_group_id"])
        data = item["gender"]
        data = ast.literal_eval(data)
        customer["gender"] = int(data["id"])
        return self._connection.customer.create(customer)

    def create_product(self, item):
        product = {i: item[i] for i in item}
        data = product.pop('product_type', None)
        data = ast.literal_eval(data)
        type = data["type"]
        data = product.pop('attribute_set_id', None)
        data = ast.literal_eval(data)
        attribute = data["set_id"]
        sku = product.pop('sku', None)
        return self._connection.catalog_product.create(type, attribute, sku, product)
