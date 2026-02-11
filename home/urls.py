from django.urls import path

from . import views

app_name = "home"

urlpatterns = [
    path("", views.index, name="index"),
    path("profile/", views.profile, name="profile"),
    path("subscription/", views.subscription, name="subscription"),
    path("root/", views.root_domain, name="root_domain"),
]
