from django import forms
from apps.gp.models import SubscriptionsList
from apps.landing.forms import DescriptionModelMultipleChoiceField


class SubscriptionsForm(forms.Form):
    subscription_list = DescriptionModelMultipleChoiceField(queryset=SubscriptionsList.objects.all(), required=False,
                                                            widget=forms.CheckboxSelectMultiple, )
