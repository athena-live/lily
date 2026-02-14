from django.shortcuts import redirect
from django.urls import reverse
from django.db.models import Q
from django.utils import timezone

from home.models import ReferralCode, ReferralSignup, SubscriptionSelection


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


class ReferralAttributionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not request.user.is_authenticated or request.session is None:
            return response
        if ReferralSignup.objects.filter(user=request.user).exists():
            return response
        ref_code_value = request.session.pop("referral_code", "")
        if not ref_code_value:
            return response
        ref_code = ReferralCode.objects.filter(code=ref_code_value, is_active=True).first()
        if not ref_code:
            return response
        ReferralSignup.objects.create(
            user=request.user, ref_code=ref_code, referred_by=ref_code.user
        )
        return response
