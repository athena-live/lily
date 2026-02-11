from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings


class AccountAdapter(DefaultAccountAdapter):
    def send_confirmation_mail(self, request, emailconfirmation, signup):
        self._confirmation_from_email = getattr(
            settings, "ACCOUNT_EMAIL_CONFIRMATION_FROM_EMAIL", None
        )
        try:
            return super().send_confirmation_mail(request, emailconfirmation, signup)
        finally:
            self._confirmation_from_email = None

    def get_from_email(self):
        confirmation_from_email = getattr(self, "_confirmation_from_email", None)
        if confirmation_from_email:
            return confirmation_from_email
        return super().get_from_email()
