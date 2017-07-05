from django import forms
from django.forms import formset_factory, inlineformset_factory
from apps.gp.models import Plug, PlugActionSpecification


class PlugSpecificationForm(forms.ModelForm):
    class Meta:
        model = PlugActionSpecification
        fields = ['plug', 'action_specification', 'value']


PlugSpecificationFormSet = inlineformset_factory(Plug, PlugActionSpecification,
                                                 fields=['plug', 'action_specification', 'value'])
