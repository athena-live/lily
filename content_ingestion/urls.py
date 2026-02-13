from django.urls import path

from . import views

app_name = "content_ingestion"

urlpatterns = [
    path("", views.ingest, name="ingest"),
]
