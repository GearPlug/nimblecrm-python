from django import forms
from apps.gp.enum import MapField


class MapForm(forms.Form):
    def __init__(self, *args, **kwargs):
        try:
            extra = kwargs.pop('extra')
            super(MapForm, self).__init__(*args, **kwargs)
            # print(extra)
            for field in extra:
                if isinstance(field, str):
                    self.fields['%s' % field] = forms.CharField(label=field, required=False)
                elif isinstance(field, dict):
                    params = {}
                    if 'label' in field:
                        params['label'] = field['label']

                    if 'name' in field:
                        name = field['name']
                    else:
                        if 'label' in params:
                            name = params['label']
                    if 'default' in field:
                        params['default'] = field['default']

                    if 'required' in field:
                        params['required'] = field['required']
                    else:
                        params['required'] = False

                    if 'options' in field and field['options']:
                        if isinstance(field['options'], list):
                            custom_field = forms.ChoiceField
                            choices = tuple('') + tuple(
                                (field['options'][choice]['name'], field['options'][choice]['value'])
                                for choice in field['options'])
                            params['choices'] = choices
                        else:
                            custom_field = forms.CharField
                            # print("no es una lista de choices")
                    else:
                        if 'len' in field:
                            try:
                                params['max_length'] = int(field['len'])
                            except:
                                params['max_length'] = 100
                        if 'type' in field:
                            if field['type'] == 'varchar' or field['type'] == 'email':
                                custom_field = forms.CharField
                            # elif field['type'] == 'email':
                            #     custom_field = forms.EmailField
                            elif field['type'] == 'boolean':
                                custom_field = forms.BooleanField
                            else:
                                custom_field = forms.CharField
                        else:
                            custom_field = forms.CharField
                    self.fields[name] = custom_field(**params)
                elif isinstance(field, MapField):
                    params = {a: getattr(field, a) for a in field.attrs if a != 'field_type' and a != 'name'}
                    field_type = getattr(field, 'field_type')
                    print(field_type)
                    if field_type in ['text', 'varchar', 'phone', 'url', 'name', 'id', 'relate', 'assigned_user_name',
                                      'email', 'image', 'fullname']:
                        custom_field = forms.CharField
                    elif field_type == 'bool':
                        if 'max_length' in params:
                            del (params['max_length'])
                        if 'choices' in params:
                            del (params['choices'])
                        custom_field = forms.BooleanField
                    elif field_type == 'enum':
                        if 'max_length' in params:
                            del (params['max_length'])
                        custom_field = forms.ChoiceField
                    elif field_type == 'date':
                        if 'max_length' in params:
                            del (params['max_length'])
                        if 'choices' in params:
                            del (params['choices'])
                        custom_field = forms.DateField
                    elif field_type == 'datetime':
                        if 'max_length' in params:
                            del (params['max_length'])
                        if 'choices' in params:
                            del (params['choices'])
                        custom_field = forms.DateTimeField
                    elif field_type == 'float':
                        length = int(params.pop('max_length'))
                        params['max_digits'] = length
                        params['decimal_places'] = 2
                        custom_field = forms.DecimalField
                    # elif field_type == 'email':
                    #     custom_field = forms.EmailField
                    try:
                        self.fields[getattr(field, 'name')] = custom_field(**params)
                    except Exception as e:
                        print(e)
                        raise
                        self.fields['custom_%s' % field] = forms.CharField(**params)
        except Exception as e:
            raise
            super(MapForm, self).__init__(*args, **kwargs)
