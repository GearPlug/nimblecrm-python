from django.conf.urls import url
from apps.user.views import SignupView, LoginView, email_test

urlpatterns = [
    url(r"^signup/$", SignupView.as_view(), name="user_signup"),
    url(r"^login/$", LoginView.as_view(), name="account_login"),
    url(r"^test/$", email_test, name="test_login"),
]
