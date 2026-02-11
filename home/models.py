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
