import account.views
import account.forms
import apps.user.forms


class SignupView(account.views.SignupView):
    form_class = apps.user.forms.SignupForm

    def generate_username(self, form):
        username = "user@ %s" % form.cleaned_data["email"]
        return username


class LoginView(account.views.LoginView):
    form_class = account.forms.LoginEmailForm
