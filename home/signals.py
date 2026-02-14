from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import ReferralCode, ReferralSignup


@receiver(post_save, sender=get_user_model())
def ensure_referral_code(sender, instance, created, **kwargs):
    if not created:
        return
    if ReferralCode.objects.filter(user=instance).exists():
        return
    ReferralCode.create_for_user(instance)


@receiver(user_logged_in)
def attach_referral_on_login(sender, request, user, **kwargs):
    if request is None or request.session is None:
        return
    if ReferralSignup.objects.filter(user=user).exists():
        return
    ref_code_value = request.session.pop("referral_code", "")
    if not ref_code_value:
        return
    ref_code = ReferralCode.objects.filter(code=ref_code_value, is_active=True).first()
    if not ref_code:
        return
    ReferralSignup.objects.create(user=user, ref_code=ref_code, referred_by=ref_code.user)
