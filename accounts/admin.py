from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html

from .models import User, Profile


# ---------------------------------------------------------------------------
# Inline
# ---------------------------------------------------------------------------

class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name = "Profile"
    verbose_name_plural = "Profile"
    fields = ("bio", "avatar", "avatar_preview", "location", "website", "date_of_birth")
    readonly_fields = ("avatar_preview",)

    def avatar_preview(self, obj):
        if obj.avatar:
            return format_html(
                '<img src="{}" style="width:80px;height:80px;border-radius:50%;object-fit:cover;" />',
                obj.avatar.url,
            )
        return "No avatar"

    avatar_preview.short_description = "Preview"


# ---------------------------------------------------------------------------
# User admin
# ---------------------------------------------------------------------------

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = (
        "email",
        "full_name",
        "is_active",
        "is_staff",
        "is_superuser",
        "date_joined",
    )
    list_display_links = ("email", "full_name")
    list_filter = ("is_active", "is_staff", "is_superuser", "date_joined")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("-date_joined",)
    readonly_fields = ("id", "date_joined", "last_login")

    fieldsets = (
        ("Identity", {"fields": ("id", "email", "password")}),
        ("Personal Info", {"fields": ("first_name", "last_name")}),
        (
            "Permissions",
            {
                "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
                "classes": ("collapse",),
            },
        ),
        ("Timestamps", {"fields": ("date_joined", "last_login"), "classes": ("collapse",)}),
    )

    add_fieldsets = (
        (
            "Create New User",
            {
                "classes": ("wide",),
                "fields": ("email", "first_name", "last_name", "password1", "password2", "is_active", "is_staff"),
            },
        ),
    )

    def full_name(self, obj):
        return obj.get_full_name() or "—"

    full_name.short_description = "Full Name"


# ---------------------------------------------------------------------------
# Profile admin (standalone)
# ---------------------------------------------------------------------------

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "location", "website", "avatar_thumb", "updated_at")
    list_display_links = ("user",)
    search_fields = ("user__email", "location", "bio")
    readonly_fields = ("user", "avatar_thumb", "created_at", "updated_at")
    ordering = ("-updated_at",)

    fieldsets = (
        ("User", {"fields": ("user",)}),
        ("Details", {"fields": ("bio", "avatar", "avatar_thumb", "location", "website", "date_of_birth")}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def avatar_thumb(self, obj):
        if obj.avatar:
            return format_html(
                '<img src="{}" style="width:50px;height:50px;border-radius:50%;object-fit:cover;" />',
                obj.avatar.url,
            )
        return "—"

    avatar_thumb.short_description = "Avatar"
