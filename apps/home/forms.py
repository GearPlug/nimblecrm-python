from django import forms
from apps.gp.models import Subscriptions, SubscriptionsList
from django.contrib.auth.models import User

class SubscriptionsForm(forms.Form):
    user_lists = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple)

    def __init__(self, *args, **kwargs):
        self.user = kwargs['initial']['owner']
        super(SubscriptionsForm, self).__init__(*args, **kwargs)

        user_obj = User.objects.get(username__exact=self.user)
        user_id = user_obj.id

        list_obj = []
        list_data = Subscriptions.objects.filter(user=user_id).values()

        for i in list_data:
            values = SubscriptionsList.objects.filter(id=i['list_id']).values()
            for y in values:
                for k, v in y.items():
                    if k == 'title':
                        list_obj.append((i['list_id'], v))

        self.fields['user_lists'].choices = list_obj


