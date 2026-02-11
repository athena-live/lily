from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.utils import timezone
from datetime import timezone as dt_timezone
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
        current_plan_name = matched or _get_stripe_service_name(current_price_id)
    context = {
        "current_plan_name": current_plan_name,
        "current_price_id": current_price_id,
        "service_plans": plans,
        "has_active_subscription": _is_subscription_active(selection),
        "cancel_at_period_end": bool(selection and selection.stripe_cancel_at_period_end),
        "cancel_at_date": _effective_cancel_date(selection),
        "cancel_in_future": bool(
            selection
            and _effective_cancel_date(selection)
            and _effective_cancel_date(selection) > timezone.now()
        ),
        "plan_start_date": selection.stripe_current_period_start if selection else None,
        "username": request.user.username,
        "subscription_status": selection.stripe_status if selection else "",
        "canceled_or_ended": bool(
            selection
            and (
                selection.stripe_status == "canceled"
                or (
                    _effective_cancel_date(selection)
                    and _effective_cancel_date(selection) <= timezone.now()
                )
            )
        ),
    }
    return render(request, "home/profile.html", context)


def _get_stripe_service_name(price_id):
    if not price_id or not settings.STRIPE_SECRET_KEY:
        return "Service details unavailable"
    try:
        stripe.api_key = settings.STRIPE_SECRET_KEY
        price = stripe.Price.retrieve(price_id, expand=["product"])
    except stripe.error.StripeError:
        return "Service details unavailable"
    product = price.get("product")
    if isinstance(product, dict):
        name = product.get("name")
        if name:
            return name
    return "Service details unavailable"


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


@login_required
def cancel_subscription(request):
    if request.method != "POST":
        return redirect("home:profile")

    selection = SubscriptionSelection.objects.filter(user=request.user).first()
    if not selection or not selection.stripe_subscription_id:
        return redirect("home:profile")

    if not settings.STRIPE_SECRET_KEY:
        return redirect("home:profile")

    stripe.api_key = settings.STRIPE_SECRET_KEY
    subscription = stripe.Subscription.modify(
        selection.stripe_subscription_id,
        cancel_at_period_end=True,
    )
    if not subscription.get("current_period_end"):
        subscription = stripe.Subscription.retrieve(selection.stripe_subscription_id)
    selection.stripe_status = subscription.get("status", "") or ""
    selection.stripe_cancel_at_period_end = bool(
        subscription.get("cancel_at_period_end")
    )
    selection.stripe_cancel_at = _from_unix_timestamp(subscription.get("cancel_at"))
    selection.stripe_current_period_start = _from_unix_timestamp(
        subscription.get("current_period_start")
    )
    selection.stripe_current_period_end = _from_unix_timestamp(
        subscription.get("current_period_end")
    )
    if selection.stripe_cancel_at_period_end and not selection.stripe_cancel_at:
        selection.stripe_cancel_at = selection.stripe_current_period_end
    selection.save()
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
    elif event["type"] in ("invoice.paid", "invoice.payment_succeeded", "invoice.finalized"):
        invoice = event["data"]["object"]
        _handle_invoice_event(invoice)
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
    selection, _ = SubscriptionSelection.objects.get_or_create(user=user)
    selection.stripe_customer_id = session.get("customer", "") or ""
    selection.save()
    _upsert_selection_from_subscription(user, subscription)


def _handle_subscription_event(subscription):
    customer_id = subscription.get("customer")
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
    if customer_id:
        selection = SubscriptionSelection.objects.filter(stripe_customer_id=customer_id).first()
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
    if not customer_email:
        customer_id = session.get("customer")
        customer_email = _get_customer_email(customer_id)
    return _resolve_user(user_id, customer_email)


def _get_user_from_subscription(subscription):
    metadata = subscription.get("metadata", {}) or {}
    user_id = metadata.get("user_id")
    customer_email = subscription.get("customer_email")
    if not customer_email:
        customer_id = subscription.get("customer")
        customer_email = _get_customer_email(customer_id)
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


def _get_customer_email(customer_id):
    if not customer_id:
        return None
    try:
        customer = stripe.Customer.retrieve(customer_id)
    except stripe.error.StripeError:
        return None
    return customer.get("email")


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
    selection.stripe_customer_id = subscription.get("customer", "") or ""
    selection.stripe_subscription_id = subscription.get("id", "") or ""
    selection.stripe_price_id = price_id or ""
    selection.stripe_product_id = product_id or ""
    selection.stripe_status = subscription.get("status", "") or ""
    selection.stripe_cancel_at_period_end = bool(
        subscription.get("cancel_at_period_end")
    )
    selection.stripe_cancel_at = _from_unix_timestamp(subscription.get("cancel_at"))
    selection.stripe_current_period_start = _from_unix_timestamp(
        subscription.get("current_period_start")
    )
    selection.stripe_current_period_end = _from_unix_timestamp(
        subscription.get("current_period_end")
    )
    if selection.stripe_cancel_at_period_end and not selection.stripe_cancel_at:
        selection.stripe_cancel_at = selection.stripe_current_period_end
    selection.save()


def _handle_invoice_event(invoice):
    user = _get_user_from_invoice(invoice)
    if not user:
        customer_id = invoice.get("customer")
        if customer_id:
            selection = SubscriptionSelection.objects.filter(
                stripe_customer_id=customer_id
            ).first()
            if selection:
                user = selection.user
    if not user:
        return

    subscription_id = invoice.get("subscription")
    price_id, product_id, period_start = _get_price_and_product_from_invoice(invoice)
    customer_id = invoice.get("customer", "") or ""

    selection, _ = SubscriptionSelection.objects.get_or_create(user=user)
    selection.stripe_customer_id = customer_id
    selection.stripe_subscription_id = subscription_id or ""
    if price_id:
        selection.stripe_price_id = price_id
    if product_id:
        selection.stripe_product_id = product_id
    if period_start:
        selection.stripe_current_period_start = period_start
    selection.save()

    if subscription_id:
        subscription = stripe.Subscription.retrieve(
            subscription_id, expand=["items.data.price.product"]
        )
        _upsert_selection_from_subscription(user, subscription)


def _get_user_from_invoice(invoice):
    customer_email = invoice.get("customer_email")
    if not customer_email:
        customer_id = invoice.get("customer")
        customer_email = _get_customer_email(customer_id)
    return _resolve_user(None, customer_email)


def _get_price_and_product_from_invoice(invoice):
    lines = (invoice.get("lines") or {}).get("data") or []
    if not lines:
        return "", "", None
    line = lines[0]
    pricing = line.get("pricing") or {}
    price_details = pricing.get("price_details") or {}
    price_id = price_details.get("price", "") or ""
    product_id = price_details.get("product", "") or ""
    if not price_id:
        price_obj = line.get("price") or line.get("plan") or {}
        if isinstance(price_obj, dict):
            price_id = price_obj.get("id", "") or ""
            product_id = product_id or price_obj.get("product", "") or ""
    if not product_id:
        product_obj = line.get("product")
        if isinstance(product_obj, dict):
            product_id = product_obj.get("id", "") or ""
        elif isinstance(product_obj, str):
            product_id = product_obj
    period = line.get("period", {})
    period_start = _from_unix_timestamp(period.get("start"))
    return price_id, product_id, period_start


def _from_unix_timestamp(value):
    if not value:
        return None
    return timezone.datetime.fromtimestamp(value, tz=dt_timezone.utc)


def _is_subscription_active(selection):
    if not selection:
        return False
    if not (selection.stripe_subscription_id or selection.stripe_price_id):
        return False
    if selection.stripe_status and selection.stripe_status not in ("active", "trialing"):
        return False
    if selection.stripe_cancel_at and selection.stripe_cancel_at <= timezone.now():
        return False
    if selection.stripe_current_period_end and selection.stripe_current_period_end <= timezone.now():
        return False
    return True


def _effective_cancel_date(selection):
    if not selection:
        return None
    if selection.stripe_cancel_at:
        return selection.stripe_cancel_at
    return selection.stripe_current_period_end


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
