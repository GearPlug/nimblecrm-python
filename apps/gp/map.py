from apps.gp.enum import ConnectorEnum


class MapField(object):
    """
    name = None
    label = None
    field_type = None
    options = None -> choices = None
    default = None
    required = False
    max_length = None
    """

    def __init__(self, d, controller=None, **kwargs):
        if controller == ConnectorEnum.SugarCRM:
            if 'name' in d:
                self.name = d['name']
            if 'label' in d:
                self.label = d['label']
            if 'options' in d:
                if isinstance(d['options'], dict):
                    self.choices = [(d['options'][choice]['name'], d['options'][choice]['value'])
                                    for choice in d['options']]
                    self.choices.insert(0, ('', ''))
            if 'type' in d:
                self.field_type = d['type']
            if 'len' in d:
                try:
                    self.max_length = int(d['len'])
                except:
                    self.max_length = 200
                    # print('field %s' % self.attrs)
        elif controller == ConnectorEnum.MailChimp:
            if 'tag' in d:
                self.name = d['tag']
            if 'name' in d:
                self.label = d['name']
            if 'required' in d:
                self.required = d['required']
            if 'default_value' in d and d['default_value'] != '':
                self.default = d['default_value']
            if 'type' in d:
                self.field_type = d['type']
            if 'options' in d:
                if 'size' in d['options']:
                    try:
                        self.max_length = int(d['options']['size'])
                    except:
                        pass
        elif controller == ConnectorEnum.Bitbucket:
            if 'name' in d:
                self.name = d['name']
                self.label = d['name']
            if 'required' in d:
                self.required = d['required']
            if 'type' in d:
                self.field_type = d['type']
            if 'values' in d:
                self.choices = [(choice, choice) for choice in d['values']]
                self.choices.insert(0, ('', ''))
        elif controller == ConnectorEnum.JIRA:
            # print(d)
            if 'id' in d:
                self.name = d['id']
            if 'name' in d:
                self.label = d['name']
            if 'required' in d:
                self.required = d['required']
            if 'schema' in d and 'type' in d['schema']:
                # Jira devuelve como Type nombres de objetos: ej. User, Issue
                # self.field_type = d['schema']['type']
                self.field_type = 'text'
            if 'allowedValues' in d and d['allowedValues']:
                self.choices = [(choice['id'], '{} ({})'.format(choice['name'], choice['id'])) for choice in
                                d['allowedValues']]
                self.choices.insert(0, ('', ''))
                self.field_type = 'choices'
        elif controller == ConnectorEnum.GetResponse:
            if 'id' in d:
                self.name = d['id']
            else:
                self.name = d['name']
            if 'name' in d:
                self.label = d['name']
            if 'required' in d:
                self.required = d['required']
            if 'type' in d:
                self.field_type = d['type']
            if 'values' in d and d['values']:
                self.choices = [(choice, choice) for choice in d['values']]
                self.choices.insert(0, ('', ''))
                self.field_type = 'choices'
        elif controller == ConnectorEnum.ZohoCRM:
            if 'type' in d:
                self.field_type = d['type']
            if 'dv' in d:
                self.name = d['dv']
            if 'label' in d:
                self.label = d['label']
            if 'req' in d:
                self.required = True if d['req'] == 'true' else False
            if 'val' in d:
                if isinstance(d['val'], list):
                    self.choices = [(choice, choice) for choice in d['val']]
                    self.choices.insert(0, ('', ''))
                    self.field_type = 'choices'
            if 'maxlength' in d:
                self.max_length = int(d['maxlength'])
        elif controller == ConnectorEnum.GoogleCalendar:
            if 'name' in d:
                self.name = d['name']
                self.label = d['name']
            if 'required' in d:
                self.required = d['required']
            if 'type' in d:
                self.field_type = d['type']
            if 'values' in d and d['values']:
                self.choices = [(choice, choice) for choice in d['values']]
                self.choices.insert(0, ('', ''))
                self.field_type = 'choices'
        elif controller == ConnectorEnum.YouTube:
            if 'name' in d:
                self.name = d['name']
                self.label = d['name']
            if 'required' in d:
                self.required = d['required']
            if 'type' in d:
                self.field_type = d['type']
            if 'values' in d and d['values']:
                self.choices = [(choice, choice) for choice in d['values']]
                self.choices.insert(0, ('', ''))
                self.field_type = 'choices'
        elif controller == ConnectorEnum.Salesforce:
            if 'name' in d:
                self.name = d['name']
            if 'label' in d:
                self.label = d['label']
            if 'nillable' in d:
                self.required = True if not d['nillable'] else False
            if 'type' in d:
                self.field_type = d['type']
            if 'picklistValues' in d and d['picklistValues']:
                self.choices = [(c['value'], c['label']) for c in d['picklistValues'] if c['active']]
                self.choices.insert(0, ('', ''))
        elif controller == ConnectorEnum.Shopify:
            if 'name' in d:
                self.name = d['name']
                self.label = d['name']
            if 'required' in d:
                self.required = d['required']
            if 'type' in d:
                self.field_type = d['type']
            if 'values' in d:
                self.choices = [(choice, choice) for choice in d['values']]
                self.choices.insert(0, ('', ''))
                self.field_type = 'choices'
        elif controller == ConnectorEnum.HubSpot:
            if 'name' in d:
                self.name = d['name']
            if 'label' in d:
                self.label = d['label']
            if 'favorited' in d:
                self.required = d['favorited']
            if 'type' in d:
                self.field_type = d['type']
            if  d['type']=='enumeration':
                self.choices = [(choice, choice) for choice in d['options']]
                self.choices.insert(0, ('', ''))
                self.field_type = 'choices'
        elif controller == ConnectorEnum.Mandrill:
            if 'name' in d:
                self.name = d['name']
                self.label = d['name']
            if 'required' in d:
                self.required = d['required']
            if 'type' in d:
                self.field_type = d['type']
            if 'values' in d and d['values']:
                self.choices = [(choice, choice) for choice in d['values']]
                self.choices.insert(0, ('', ''))
                self.field_type = 'choices'
        else:
            if 'name' in d:
                self.name = d['name']
            if 'label' in d:
                self.label = d['label']
            if 'default' in d or 'default_value' in d:
                self.default = d['default'] if 'default' in d else d['default_value']
            if 'options' in d:
                if isinstance(d['options'], dict):
                    self.choices = [(d['options'][choice]['name'], d['options'][choice]['value'])
                                    for choice in d['options']]
                    self.choices.insert(0, ('', ''))
            self.required = False

    @property
    def attrs(self):
        return [key for key, value in self.__dict__.items()]
