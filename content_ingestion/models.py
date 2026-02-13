from django.conf import settings
from django.db import models


class IngestedContent(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ingested_contents",
    )
    name = models.CharField(max_length=200)
    raw_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"IngestedContent(id={self.id}, name={self.name})"
