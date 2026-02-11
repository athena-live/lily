from django.shortcuts import redirect
from django.urls import reverse

from home.models import SubscriptionSelection


class SubscriptionRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.subscription_path = None

    def __call__(self, request):
        if self.subscription_path is None:
            self.subscription_path = reverse("home:subscription")

        if request.user.is_authenticated:
            path = request.path
            if (
                path.startswith("/static/")
                or path.startswith("/media/")
                or path.startswith("/accounts/")
                or path.startswith("/admin/")
                or path == self.subscription_path
            ):
                return self.get_response(request)

            if not SubscriptionSelection.objects.filter(user=request.user).exists():
                return redirect(self.subscription_path)

        return self.get_response(request)
