from django.conf import settings
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib.auth.decorators import login_required

from .models import SubscriptionSelection
# Create your views here.


def index(request):
    return render(request, "home/index.html")


@login_required
def profile(request):
    selection = SubscriptionSelection.objects.filter(user=request.user).first()
    plans = getattr(settings, "SUBSCRIPTION_PLANS", [])
    current_price_id = selection.stripe_price_id if selection else ""
    current_plan_name = "No service selected"
    if current_price_id:
        matched = next(
            (plan["name"] for plan in plans if plan.get("price_id") == current_price_id),
            None,
        )
        current_plan_name = matched or f"Service ID {current_price_id}"
    context = {
        "current_plan_name": current_plan_name,
        "current_price_id": current_price_id,
        "service_plans": plans,
    }
    return render(request, "home/profile.html", context)


@login_required
def subscription(request):
    selection = SubscriptionSelection.objects.filter(user=request.user).first()
    if request.method == "POST":
        if selection is None:
            selection = SubscriptionSelection(user=request.user)
        posted_price_id = request.POST.get("price_id", "").strip()
        allowed_price_ids = {
            plan.get("price_id")
            for plan in getattr(settings, "SUBSCRIPTION_PLANS", [])
            if plan.get("price_id")
        }
        if posted_price_id and (not allowed_price_ids or posted_price_id in allowed_price_ids):
            selection.stripe_price_id = posted_price_id
        selection.save()

        next_url = request.POST.get("next", "").strip()
        if next_url and url_has_allowed_host_and_scheme(
            next_url, allowed_hosts={request.get_host()}
        ):
            return redirect(next_url)
        return redirect("home:profile")

    context = {
        "stripe_pricing_table_id": settings.STRIPE_PRICING_TABLE_ID,
        "stripe_publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
        "subscription_selected": selection is not None,
    }
    return render(request, "home/subscription.html", context)


def root_domain(request):
    host = request.get_host().split(":")[0].strip(".")
    parts = [p for p in host.split(".") if p]
    if len(parts) < 2:
        target_host = host
    else:
        second_level_tlds = {
            "ac",
            "co",
            "com",
            "edu",
            "gov",
            "net",
            "org",
        }
        if len(parts) >= 3 and len(parts[-1]) == 2 and parts[-2] in second_level_tlds:
            target_host = ".".join(parts[-3:])
        else:
            target_host = ".".join(parts[-2:])

    target_url = f"{request.scheme}://{target_host}"
    if not url_has_allowed_host_and_scheme(target_url, allowed_hosts={target_host}):
        return HttpResponseRedirect("/")
    return HttpResponseRedirect(target_url)
