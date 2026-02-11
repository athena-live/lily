from django.urls import path

from . import views

app_name = "home"

urlpatterns = [
    path("", views.index, name="index"),
    path("profile/", views.profile, name="profile"),
    path("subscription/", views.subscription, name="subscription"),
    path("subscription/change/", views.change_subscription, name="change_subscription"),
    path("stripe/webhook/", views.stripe_webhook, name="stripe_webhook"),
    path("root/", views.root_domain, name="root_domain"),
]
