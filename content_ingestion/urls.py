from django.urls import path

from . import views

app_name = "content_ingestion"

urlpatterns = [
    path("", views.ingest, name="ingest"),
    path("list/", views.ingest_list, name="list"),
    path("<int:content_id>/", views.ingest_detail, name="detail"),
    path("<int:content_id>/edit/", views.ingest_edit, name="edit"),
    path("<int:content_id>/delete/", views.ingest_delete, name="delete"),
]
