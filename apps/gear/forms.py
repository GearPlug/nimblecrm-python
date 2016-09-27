from django import forms


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
                    # else:
                    params = {'required': False}
                    if 'label' in field:
                        params['label'] = field['label']

                    if 'name' in field:
                        name = field['name']
                    else:
                        if 'label' in params:
                            name = params['label']
                    if 'default' in field:
                        params['default'] = field['default']

                    if 'options' in field and field['options']:
                        custom_field = forms.ChoiceField
                        choices = tuple('') + tuple(
                            (field['options'][choice]['name'], field['options'][choice]['value'])
                            for choice in field['options'])
                        params['choices'] = choices
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
                # print('name: %s, %s, %s' % (name, custom_field, params))
                # if custom_field != forms.ChoiceField:
                self.fields[name] = custom_field(**params)
        except Exception as e:
            print(e)
            super(MapForm, self).__init__(*args, **kwargs)
