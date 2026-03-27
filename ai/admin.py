from django.contrib import admin
from .models import GeminiUsage


@admin.register(GeminiUsage)
class GeminiUsageAdmin(admin.ModelAdmin):
    list_display = ("task", "model", "user", "total_tokens", "success", "created_at")
    list_filter = ("model", "task", "success")
    search_fields = ("user__email",)
    raw_id_fields = ("user",)
    readonly_fields = ("id", "created_at", "updated_at")
