from django.urls import path

from . import views


app_name = "slop_detection"

urlpatterns = [
    path("analyze/<int:content_id>/", views.analyze, name="analyze"),
    path("report/<int:report_id>/", views.report_detail, name="report_detail"),
    path("latest/<int:content_id>/", views.latest_report, name="latest_report"),
]
