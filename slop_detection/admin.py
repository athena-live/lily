from django.contrib import admin

from .models import ContentCorrection, FineTuneJob, SiteModelConfig, SlopReport


@admin.register(SlopReport)
class SlopReportAdmin(admin.ModelAdmin):
    list_display = ("id", "content", "user", "created_at")
    search_fields = ("content__name", "user__email")
    list_filter = ("created_at",)


@admin.register(ContentCorrection)
class ContentCorrectionAdmin(admin.ModelAdmin):
    list_display = ("id", "content", "editor", "is_current", "created_at")
    search_fields = ("content__name", "editor__email")
    list_filter = ("is_current", "created_at")


@admin.register(FineTuneJob)
class FineTuneJobAdmin(admin.ModelAdmin):
    list_display = ("id", "job_id", "status", "base_model", "fine_tuned_model", "created_at")
    search_fields = ("job_id", "fine_tuned_model", "base_model")
    list_filter = ("status", "created_at")


@admin.register(SiteModelConfig)
class SiteModelConfigAdmin(admin.ModelAdmin):
    list_display = ("id", "current_model", "updated_by", "updated_at")

# Register your models here.
