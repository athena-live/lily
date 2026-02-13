from django.urls import path

from . import views


app_name = "slop_detection"

urlpatterns = [
    path("analyze/<int:content_id>/", views.analyze, name="analyze"),
]
