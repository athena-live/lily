from django.urls import path

from . import views

app_name = "home"

urlpatterns = [
    path("", views.index, name="index"),
    path("profile/", views.profile, name="profile"),
    path("subscription/", views.subscription, name="subscription"),
    path("subscription/status/", views.subscription_status, name="subscription_status"),
    path("subscription/change/", views.change_subscription, name="change_subscription"),
    path("subscription/cancel/", views.cancel_subscription, name="cancel_subscription"),
    path("referral/generate/", views.generate_referral_code, name="generate_referral_code"),
    path("theme/", views.set_theme, name="set_theme"),
    path("stripe/webhook/", views.stripe_webhook, name="stripe_webhook"),
    path("root/", views.root_domain, name="root_domain"),
]
