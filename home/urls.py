from django.urls import path

from . import views

app_name = "home"

urlpatterns = [
    path("", views.index, name="index"),
    path("root/", views.root_domain, name="root_domain"),
]
