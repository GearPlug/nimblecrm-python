from allauth.account.forms import SignupForm
from django import forms
from django.utils.translation import gettext as _
from apps.gp.models import SubscriptionsList


class DescriptionModelMultipleChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return obj.description


class NameSignupForm(SignupForm):
    email = forms.EmailField(label=_("Email"),
                             widget=forms.TextInput(
                                 attrs={'type': 'email', 'placeholder': _('Email'), 'class': 'input-form form-control',
                                        'autocomplete': 'off'}))
    first_name = forms.CharField(max_length=30, label=_('First name'),
                                 widget=forms.TextInput(
                                     attrs={'type': 'text', 'placeholder': _('First name'),
                                            'class': 'input-form form-control'}))
    last_name = forms.CharField(max_length=30, label=_('Last name'),
                                widget=forms.TextInput(
                                    attrs={'type': 'text', 'placeholder': _('Last name'),
                                           'class': 'input-form form-control'}))
    subscription_list = DescriptionModelMultipleChoiceField(queryset=SubscriptionsList.objects.all(), required=False,
                                                            widget=forms.CheckboxSelectMultiple, )

    def __init__(self, *args, **kwargs):
        super(NameSignupForm, self).__init__(*args, **kwargs)
        self.fields['password1'] = forms.CharField(label=_("Password"), widget=forms.PasswordInput(
            attrs={'class': 'input-form form-control', 'placeholder': _('Password')}))
