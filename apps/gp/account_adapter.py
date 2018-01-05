from django.shortcuts import reverse
from allauth.account.adapter import DefaultAccountAdapter
from allauth.utils import build_absolute_uri


class MyAccountAdapter(DefaultAccountAdapter):
    def get_email_confirmation_url(self, request, emailconfirmation):
        """
        Forces request=None to get the current SITE.
        """
        url = reverse("account_confirm_email", args=[emailconfirmation.key])
        ret = build_absolute_uri(None, url)
        return ret
