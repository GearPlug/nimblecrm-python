from django.conf.urls import url
from apps.user.views import SignupView, LoginView

urlpatterns = [
    url(r"^signup/$", SignupView.as_view(), name="user_signup"),
    url(r"^login/$", LoginView.as_view(), name="account_login"),
]