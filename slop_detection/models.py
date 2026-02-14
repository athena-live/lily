from django.conf import settings
from django.db import models
from django.db.models import Q

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


class SlopReportCorrection(models.Model):
    report = models.ForeignKey(
        SlopReport,
        on_delete=models.CASCADE,
        related_name="corrections",
    )
    editor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="slop_report_corrections",
    )
    original_report = models.JSONField()
    corrected_report = models.JSONField()
    notes = models.TextField(blank=True, default="")
    is_current = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"SlopReportCorrection(id={self.id}, report_id={self.report_id})"


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


class SlopRateLimitUsage(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="slop_rate_limits",
    )
    ip_address = models.CharField(max_length=45, blank=True, default="")
    date = models.DateField()
    count = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "date"],
                condition=Q(user__isnull=False),
                name="slop_rate_limit_user_date_unique",
            ),
            models.UniqueConstraint(
                fields=["ip_address", "date"],
                condition=Q(user__isnull=True),
                name="slop_rate_limit_ip_date_unique",
            ),
        ]

    def __str__(self):
        owner = self.user_id or self.ip_address or "unknown"
        return f"SlopRateLimitUsage(owner={owner}, date={self.date}, count={self.count})"
