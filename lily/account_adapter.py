from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings

from home.models import ReferralCode, ReferralSignup


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

    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=commit)
        if not request:
            return user
        ref_code_value = request.session.pop("referral_code", "")
        if not ref_code_value:
            return user
        if ReferralSignup.objects.filter(user=user).exists():
            return user
        ref_code = ReferralCode.objects.filter(code=ref_code_value, is_active=True).first()
        if not ref_code:
            return user
        ReferralSignup.objects.create(user=user, ref_code=ref_code, referred_by=ref_code.user)
        return user
