import account.views
import account.forms
import apps.user.forms
from django.shortcuts import render
from django.conf import settings


class SignupView(account.views.SignupView):
    form_class = apps.user.forms.SignupForm

    def generate_username(self, form):
        username = form.cleaned_data["email"]
        return username

    def user_credentials(self):
        self.identifier_field = 'email'
        return super(SignupView, self).user_credentials()

    # def form_valid(self, form):
    #     print("SI")
    #     return super(SignupView, self).form_valid(form)
    #
    # def form_invalid(self, form):
    #     print(form.errors)
    #     return super(SignupView, self).form_invalid(form)


class LoginView(account.views.LoginView):
    form_class = account.forms.LoginEmailForm


def email_test(request):
    from apps.gp.tasks import update_gears
    update_gears.delay()
    # from django.core.mail import send_mail
    # send_mail('Subject here', 'Here is the message.', settings.EMAIL_HOST_USER, ['tavito.286@gmail.com'],
    #           fail_silently=False)
    return render(request, 'home/dashboard.html', {})
