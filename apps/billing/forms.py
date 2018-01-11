from django import forms
from apps.billing.models import ServiceRecharge


class ServiceRechargeForm(forms.ModelForm):
    recharge_amount = forms.DecimalField(decimal_places=4, max_digits=10, initial=20,
                                         widget=forms.NumberInput(attrs={'min': 20, 'step': 1}))

    class Meta:
        model = ServiceRecharge
        fields = ['recharge_amount', ]
