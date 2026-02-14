from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import ReferralCode


@receiver(post_save, sender=get_user_model())
def ensure_referral_code(sender, instance, created, **kwargs):
    if not created:
        return
    if ReferralCode.objects.filter(user=instance).exists():
        return
    ReferralCode.create_for_user(instance)
