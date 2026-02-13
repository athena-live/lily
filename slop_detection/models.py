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
