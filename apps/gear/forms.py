from django import forms
from apps.gp.map import MapField
from apps.gp.models import GearFilter
from django.forms import modelformset_factory

class MapForm(forms.Form):
    def __init__(self, *args, **kwargs):
        try:
            extra = kwargs.pop('extra')
            super(MapForm, self).__init__(*args, **kwargs)
            # print(extra)
            for field in extra:
                if isinstance(field, MapField):
                    params = {a: getattr(field, a) for a in field.attrs if a != 'field_type' and a != 'name'}
                    field_type = getattr(field, 'field_type')
                    # print(field_type)
                    if field_type in ['text', 'varchar', 'phone', 'url', 'name', 'id', 'relate', 'assigned_user_name',
                                      'email', 'image', 'fullname', 'relate', 'string']:
                        custom_field = forms.CharField
                    elif field_type == 'bool' or field_type == 'boolean':
                        if 'max_length' in params:
                            del (params['max_length'])
                        if 'choices' in params:
                            del (params['choices'])
                        # No permitir boolean requeridos o siempre tendrán que marcar el checkbox en el Mapeo
                        params['required'] = False
                        custom_field = forms.BooleanField
                    elif field_type in ['enum', 'radioenum', 'choices', 'Pick List', 'picklist']:
                        if 'max_length' in params:
                            del (params['max_length'])
                        custom_field = forms.ChoiceField
                    elif field_type == 'date':
                        if 'max_length' in params:
                            del (params['max_length'])
                        if 'choices' in params:
                            del (params['choices'])
                        custom_field = forms.CharField  # DateFieldDateField
                    elif field_type == 'datetime':
                        if 'max_length' in params:
                            del (params['max_length'])
                        if 'choices' in params:
                            del (params['choices'])
                        custom_field = forms.CharField  # DateTimeField
                    elif field_type == 'float':
                        length = int(params.pop('max_length'))
                        params['max_digits'] = length
                        params['decimal_places'] = 2
                        custom_field = forms.DecimalField
                    else:
                        custom_field = forms.CharField
                    # elif field_type == 'email':
                    #     custom_field = forms.EmailField
                    if 'required' not in params:
                        params['required'] = False

                    try:

                        self.fields[getattr(field, 'name')] = custom_field(**params)
                    except Exception as e:
                        # print(e)
                        print(field_type)
                        print(custom_field)
                        print(params)
                        raise
                        self.fields['custom_%s' % field] = forms.CharField(**params)
                else:
                    raise Exception("Not supported MapField.")
        except Exception as e:
            raise
            super(MapForm, self).__init__(*args, **kwargs)


class SendHistoryForm(forms.Form):
    date_from = forms.DateTimeField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    date_to = forms.DateTimeField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    order = forms.ChoiceField(required=True, choices=(('asc', 'Ascending'), ('desc', 'Descending')),
                              widget=forms.Select(attrs={'class': 'form-control'}))
    sent = forms.ChoiceField(required=True, choices=((0, 'All'), (True, 'Successful'), (False, 'Failed')),
                             widget=forms.Select(attrs={'class': 'form-control'}))


class DownloadHistoryForm(forms.Form):
    date_from = forms.DateTimeField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    date_to = forms.DateTimeField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    order = forms.ChoiceField(required=True, choices=(('asc', 'Ascending'), ('desc', 'Descending')),
                              widget=forms.Select(attrs={'class': 'form-control'}))


class FiltersForm(forms.ModelForm):
    class Meta:
        model = GearFilter
        fields = ('field_name', 'option', 'comparison_data', 'is_active')
        exclude = ('gear',)