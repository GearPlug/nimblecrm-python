from django.contrib.auth import get_user_model
from django import forms
from apps.gp.models import Subscriptions, SubscriptionsList

class SignupForm(forms.ModelForm):

    class Meta:
        model = Subscriptions
        fields = ('list',)

    # query = SubscriptionsList.objects.values()
    # for i in query:
    #     print(i)
    #     list = forms.ModelMultipleChoiceField(queryset=i ,widget=forms.CheckboxSelectMultiple)

    # A custom method required to work with django-allauth, see
    # https://stackoverflow.com/questions/12303478/how-to-customize-user-profile-when-using-django-allauth
    def signup(self, request, user):
        print('1')
        profile = Subscriptions()
        profile.user = user
        print(self.cleaned_data)
        list_name = self.cleaned_data['list']
        s_list = SubscriptionsList.objects.all().values()
        for i in s_list:
            if str(i['title']) == str(list_name):
                profile.list_id = i['id']
        profile.save()

class OptionsForm(forms.Form):
    OPTIONS = (
        ("a", "A"),
        ("b", "B"),
    )
    name = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple,
                                     choices=OPTIONS)

    def signup(self, request, user):
        profile = Subscriptions()
        profile.user = user
        print('user name:', profile.user)
        list_name = self.cleaned_data['list']
        s_list = SubscriptionsList.objects.all().values()
        print(s_list)
        for i in s_list:
            print('nombre de lista: {0}, titulo: {1}, id: {2}'.format(list_name, i['title'], i['id']))
            if str(i['title']) == str(list_name):
                profile.list_id = i['id']
        print('list id:', profile.list_id)
        profile.save()