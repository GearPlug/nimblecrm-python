from django import forms
from django.forms import formset_factory, inlineformset_factory
from apps.gp.models import Plug, PlugSpecification


class PlugSpecificationForm(forms.ModelForm):
    class Meta:
        model = PlugSpecification
        fields = ['plug', 'action_specification', 'value']


PlugSpecificationFormSet = inlineformset_factory(Plug, PlugSpecification,
                                                 fields=['plug', 'action_specification', 'value'])
