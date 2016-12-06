from django.conf.urls import url
from apps.user.views import SignupView, LoginView, email_test, async_spreadsheet_info, async_spreadsheet_values

urlpatterns = [
    url(r"^signup/$", SignupView.as_view(), name="user_signup"),
    url(r"^login/$", LoginView.as_view(), name="account_login"),
    url(r"^test/$", email_test, name="test_login"),
    url(r"^async/spreadsheet/info/(?P<id>.+)/$", async_spreadsheet_info, name="async_test"),
    url(r"^async/spreadsheet/values/(?P<id>.+)/(?P<sheet_id>.+)/$", async_spreadsheet_values, name="async_test"),
]
