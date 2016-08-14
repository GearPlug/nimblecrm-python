from django import forms
from apps.gp.models import Connector


class SelectConnectorForm(forms.Form):
    connector = forms.ModelChoiceField(queryset=Connector.objects.filter(is_active=True),
                                       widget=forms.RadioSelect(),
                                       initial=1)
