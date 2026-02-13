from django.contrib import admin

from .models import IngestedContent


@admin.register(IngestedContent)
class IngestedContentAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "user", "created_at")
    search_fields = ("name", "raw_text", "user__username", "user__email")
    list_filter = ("created_at",)

# Register your models here.
