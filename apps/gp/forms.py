from django.contrib.auth import get_user_model
from django import forms
from apps.gp.models import Subscriptions, SubscriptionsList

class SignupForm(forms.ModelForm):
    list = forms.ModelMultipleChoiceField(queryset=SubscriptionsList.objects.all(), widget=forms.CheckboxSelectMultiple)

    class Meta:
        model = SubscriptionsList
        fields = ('list',)

    def signup(self, request, user):
        selected_list = []
        for i in self.cleaned_data['list']:
            selected_list.append(i)
            profile = Subscriptions()

            profile.user = user
            # for i in self.cleaned_data['list']:
            #     selected_list.append(i)
            for i in selected_list:
                list = SubscriptionsList.objects.filter(title__exact=i).values()
                for y in list.iterator():
                    profile.list_id = y['id']
                    print('list id: ', profile.list_id)
                profile.save()
