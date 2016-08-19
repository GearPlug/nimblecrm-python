from django import forms


class MapForm(forms.Form):
    plug_id = forms.DecimalField()

    def __init__(self, *args, **kwargs):
        try:
            extra = kwargs.pop('extra')
            super(MapForm, self).__init__(*args, **kwargs)
            for i, field in enumerate(extra):
                self.fields[field] = forms.CharField(label=field)
        except:
            print("FORM: no extra")