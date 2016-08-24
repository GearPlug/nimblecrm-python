from django import forms


class MapForm(forms.Form):
    def __init__(self, *args, **kwargs):
        try:
            extra = kwargs.pop('extra')
            super(MapForm, self).__init__(*args, **kwargs)
            for field in extra:
                self.fields['%s' % field] = forms.CharField(label=field)
        except:
            super(MapForm, self).__init__(*args, **kwargs)
