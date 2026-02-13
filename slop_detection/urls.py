from django.urls import path

from . import views


app_name = "slop_detection"

urlpatterns = [
    path("analyze/<int:content_id>/", views.analyze, name="analyze"),
    path("report/<int:report_id>/", views.report_detail, name="report_detail"),
    path("latest/<int:content_id>/", views.latest_report, name="latest_report"),
    path("admin/ingestions/", views.admin_ingestions, name="admin_ingestions"),
    path("admin/ingestions/<int:content_id>/", views.admin_correction, name="admin_correction"),
    path("admin/training/", views.admin_training, name="admin_training"),
    path("admin/model/", views.admin_set_model, name="admin_set_model"),
]
