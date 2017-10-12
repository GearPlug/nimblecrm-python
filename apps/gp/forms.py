from django.contrib.auth import get_user_model
from django import forms
from apps.gp.models import CustomsUserFields

class SignupForm(forms.ModelForm):
    class Meta:
        model = CustomsUserFields
        fields = ('is_subcribe')

    # A custom method required to work with django-allauth, see https://stackoverflow.com/questions/12303478/how-to-customize-user-profile-when-using-django-allauth
    def signup(self, request, user):
        # Save your user
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.save()

        # Save your profile
        profile = CustomsUserFields()
        profile.user = user
        profile.phone = self.cleaned_data['phone']
        profile.type = self.cleaned_data['type']
        profile.is_subscribe = self.cleaned_data['is_subscribe']
        profile.save()