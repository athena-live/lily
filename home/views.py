from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

import stripe

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
        "has_active_subscription": bool(selection and selection.stripe_subscription_id),
    }
    return render(request, "home/profile.html", context)


@login_required
def subscription(request):
    selection = SubscriptionSelection.objects.filter(user=request.user).first()
    context = {
        "stripe_pricing_table_id": settings.STRIPE_PRICING_TABLE_ID,
        "stripe_publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
        "subscription_selected": bool(selection and selection.stripe_subscription_id),
        "client_reference_id": str(request.user.id),
        "customer_email": request.user.email,
    }
    return render(request, "home/subscription.html", context)


@login_required
def change_subscription(request):
    if request.method != "POST":
        return redirect("home:profile")

    selection = SubscriptionSelection.objects.filter(user=request.user).first()
    if not selection or not selection.stripe_subscription_id:
        return redirect("home:subscription")

    posted_price_id = request.POST.get("price_id", "").strip()
    allowed_price_ids = {
        plan.get("price_id")
        for plan in getattr(settings, "SUBSCRIPTION_PLANS", [])
        if plan.get("price_id")
    }
    if not posted_price_id or posted_price_id not in allowed_price_ids:
        return redirect("home:profile")

    if not settings.STRIPE_SECRET_KEY:
        return redirect("home:profile")

    stripe.api_key = settings.STRIPE_SECRET_KEY
    subscription = stripe.Subscription.retrieve(
        selection.stripe_subscription_id,
        expand=["items.data.price.product"],
    )
    if not subscription or not subscription.get("items", {}).get("data"):
        return redirect("home:profile")

    item_id = subscription["items"]["data"][0]["id"]
    stripe.Subscription.modify(
        selection.stripe_subscription_id,
        items=[{"id": item_id, "price": posted_price_id}],
        proration_behavior="create_prorations",
    )
    return redirect("home:profile")


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    signature = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    if not settings.STRIPE_WEBHOOK_SECRET:
        return HttpResponse(status=400)

    try:
        event = stripe.Webhook.construct_event(
            payload, signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    stripe.api_key = settings.STRIPE_SECRET_KEY

    if event["type"] in (
        "checkout.session.completed",
        "checkout.session.async_payment_succeeded",
    ):
        session = event["data"]["object"]
        _handle_checkout_session(session)
    elif event["type"] in ("customer.subscription.created", "customer.subscription.updated"):
        subscription = event["data"]["object"]
        _handle_subscription_event(subscription)
    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        _handle_subscription_deleted(subscription)

    return HttpResponse(status=200)


def _handle_checkout_session(session):
    subscription_id = session.get("subscription")
    if not subscription_id:
        return

    user = _get_user_from_session(session)
    if not user:
        return

    subscription = stripe.Subscription.retrieve(
        subscription_id, expand=["items.data.price.product"]
    )
    _upsert_selection_from_subscription(user, subscription)


def _handle_subscription_event(subscription):
    subscription_id = subscription.get("id")
    if subscription_id:
        subscription = stripe.Subscription.retrieve(
            subscription_id, expand=["items.data.price.product"]
        )
    selection = SubscriptionSelection.objects.filter(
        stripe_subscription_id=subscription.get("id", "")
    ).first()
    if selection:
        _upsert_selection_from_subscription(selection.user, subscription)
        return

    user = _get_user_from_subscription(subscription)
    if not user:
        return
    _upsert_selection_from_subscription(user, subscription)


def _handle_subscription_deleted(subscription):
    selection = SubscriptionSelection.objects.filter(
        stripe_subscription_id=subscription.get("id", "")
    ).first()
    if selection:
        selection.delete()
        return

    user = _get_user_from_subscription(subscription)
    if not user:
        return
    SubscriptionSelection.objects.filter(user=user).delete()


def _get_user_from_session(session):
    user_id = session.get("client_reference_id")
    customer_email = session.get("customer_email")
    return _resolve_user(user_id, customer_email)


def _get_user_from_subscription(subscription):
    metadata = subscription.get("metadata", {}) or {}
    user_id = metadata.get("user_id")
    customer_email = subscription.get("customer_email")
    return _resolve_user(user_id, customer_email)


def _resolve_user(user_id, customer_email):
    User = get_user_model()
    if user_id:
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None
    if customer_email:
        try:
            return User.objects.get(email__iexact=customer_email)
        except User.DoesNotExist:
            return None
    return None


def _upsert_selection_from_subscription(user, subscription):
    items = subscription.get("items", {}).get("data", [])
    price = items[0]["price"] if items else None
    price_id = price.get("id") if price else ""
    product = price.get("product") if price else ""
    if isinstance(product, dict):
        product_id = product.get("id", "")
    else:
        product_id = product or ""

    selection, _ = SubscriptionSelection.objects.get_or_create(user=user)
    selection.stripe_subscription_id = subscription.get("id", "") or ""
    selection.stripe_price_id = price_id or ""
    selection.stripe_product_id = product_id or ""
    selection.save()


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
