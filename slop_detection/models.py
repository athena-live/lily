from django.conf import settings
from django.db import models

from content_ingestion.models import IngestedContent


class SlopReport(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="slop_reports",
    )
    content = models.ForeignKey(
        IngestedContent,
        on_delete=models.CASCADE,
        related_name="slop_reports",
    )
    report = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"SlopReport(id={self.id}, content_id={self.content_id})"


class ContentCorrection(models.Model):
    content = models.ForeignKey(
        IngestedContent,
        on_delete=models.CASCADE,
        related_name="corrections",
    )
    editor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="content_corrections",
    )
    original_text = models.TextField()
    corrected_text = models.TextField()
    notes = models.TextField(blank=True, default="")
    is_current = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"ContentCorrection(id={self.id}, content_id={self.content_id})"


class FineTuneJob(models.Model):
    STATUS_CHOICES = [
        ("queued", "Queued"),
        ("running", "Running"),
        ("succeeded", "Succeeded"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fine_tune_jobs",
    )
    training_file_id = models.CharField(max_length=200)
    job_id = models.CharField(max_length=200)
    base_model = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="queued")
    fine_tuned_model = models.CharField(max_length=200, blank=True, default="")
    metadata = models.JSONField(blank=True, default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"FineTuneJob(id={self.id}, job_id={self.job_id})"


class SiteModelConfig(models.Model):
    current_model = models.CharField(max_length=200, default="gpt-4o-mini")
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="model_configs",
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"SiteModelConfig(id={self.id}, current_model={self.current_model})"
