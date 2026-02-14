from django.shortcuts import redirect
from django.urls import reverse
from django.db.models import Q
from django.utils import timezone

from home.models import SubscriptionSelection


class SubscriptionRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.subscription_path = None

    def __call__(self, request):
        if self.subscription_path is None:
            self.subscription_path = reverse("home:subscription")

        if request.user.is_authenticated:
            if request.user.is_staff or request.user.is_superuser:
                return self.get_response(request)
            path = request.path
            if (
                path.startswith("/static/")
                or path.startswith("/media/")
                or path.startswith("/accounts/")
                or path.startswith("/admin/")
                or path == self.subscription_path
            ):
                return self.get_response(request)

            has_subscription = (
                SubscriptionSelection.objects.filter(user=request.user)
                .filter(
                    Q(stripe_subscription_id__isnull=False, stripe_subscription_id__gt="")
                    | Q(stripe_price_id__isnull=False, stripe_price_id__gt="")
                )
                .exclude(stripe_status__gt="", stripe_status__in=["canceled", "incomplete_expired"])
                .exclude(stripe_cancel_at__isnull=False, stripe_cancel_at__lte=timezone.now())
                .exclude(
                    stripe_current_period_end__isnull=False,
                    stripe_current_period_end__lte=timezone.now(),
                )
            )
            if not has_subscription.exists():
                return redirect(self.subscription_path)

        return self.get_response(request)


class ReferralCaptureMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ref_code = (request.GET.get("ref") or request.GET.get("ref_code") or "").strip()
        if ref_code and request.session is not None:
            request.session["referral_code"] = ref_code
        return self.get_response(request)
