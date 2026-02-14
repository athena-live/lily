import secrets
import string

from django.conf import settings
from django.db import models


class SubscriptionSelection(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscription"
    )
    stripe_product_id = models.CharField(max_length=200, blank=True)
    stripe_price_id = models.CharField(max_length=200, blank=True)
    stripe_subscription_id = models.CharField(max_length=200, blank=True)
    stripe_customer_id = models.CharField(max_length=200, blank=True)
    stripe_status = models.CharField(max_length=50, blank=True)
    stripe_cancel_at_period_end = models.BooleanField(default=False)
    stripe_cancel_at = models.DateTimeField(null=True, blank=True)
    stripe_current_period_start = models.DateTimeField(null=True, blank=True)
    stripe_current_period_end = models.DateTimeField(null=True, blank=True)
    selected_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"SubscriptionSelection(user_id={self.user_id})"


class UserThemePreference(models.Model):
    THEME_LIGHT = "light"
    THEME_DARK = "dark"
    THEME_CHOICES = [
        (THEME_LIGHT, "Light"),
        (THEME_DARK, "Dark"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="theme_preference"
    )
    theme = models.CharField(max_length=10, choices=THEME_CHOICES, default=THEME_LIGHT)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"UserThemePreference(user_id={self.user_id}, theme={self.theme})"


class ReferralCode(models.Model):
    CODE_LENGTH = 10
    CODE_ALPHABET = string.ascii_uppercase + string.digits

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="referral_codes"
    )
    code = models.CharField(max_length=32, unique=True, db_index=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"ReferralCode(user_id={self.user_id}, code={self.code})"

    @classmethod
    def _generate_code(cls, length=None):
        size = length or cls.CODE_LENGTH
        return "".join(secrets.choice(cls.CODE_ALPHABET) for _ in range(size))

    @classmethod
    def create_for_user(cls, user):
        for _ in range(5):
            candidate = cls._generate_code()
            if not cls.objects.filter(code=candidate).exists():
                return cls.objects.create(user=user, code=candidate)
        candidate = cls._generate_code(cls.CODE_LENGTH + 4)
        return cls.objects.create(user=user, code=candidate)


class ReferralSignup(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="referral_signup"
    )
    ref_code = models.ForeignKey(
        ReferralCode, on_delete=models.SET_NULL, null=True, blank=True, related_name="signups"
    )
    referred_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="referrals_sent",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"ReferralSignup(user_id={self.user_id}, ref_code_id={self.ref_code_id})"
