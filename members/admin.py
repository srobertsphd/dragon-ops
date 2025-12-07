from django.contrib import admin
from django import forms
from django.db import models
from django.urls import path
from .models import Member, MemberType, PaymentMethod, Payment
from .admin_views import deactivate_expired_members_view


@admin.register(MemberType)
class MemberTypeAdmin(admin.ModelAdmin):
    list_display = [
        "member_type",
        "member_dues",
        "num_months",
    ]
    list_filter = []
    search_fields = ["member_type"]
    ordering = ["member_type"]


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ["payment_method"]
    list_filter = []
    search_fields = ["payment_method"]
    ordering = ["payment_method"]


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    formfield_overrides = {
        models.TextField: {"widget": forms.Textarea(attrs={"rows": 2, "cols": 50})},
    }

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "home_phone":
            kwargs["widget"] = forms.TextInput(
                attrs={
                    "placeholder": "(555) 123-4567",
                    "pattern": r"\(\d{3}\) \d{3}-\d{4}",
                    "title": "Phone format: (123) 456-7890",
                    "class": "phone-format",
                }
            )
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    class Media:
        js = ("members/js/phone_format.js",)

    list_display = [
        "member_id",
        "first_name",
        "last_name",
        "member_type",
        "status",
        "expiration_date",
        "home_phone",
    ]
    list_filter = ["member_type", "status", "home_state"]
    search_fields = [
        "member_id",
        "first_name",
        "last_name",
        "email",
        "home_phone",
    ]
    ordering = ["member_id"]
    readonly_fields = ["member_uuid", "created_at", "updated_at"]

    fieldsets = (
        (
            "Member Identification",
            {
                "fields": (
                    "member_uuid",
                    "member_id",
                    "preferred_member_id",
                    "member_type",
                ),
            },
        ),
        (
            "Personal Information",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "email",
                    "milestone_date",
                    "date_joined",
                ),
            },
        ),
        (
            "Membership Status",
            {
                "fields": ("status", "expiration_date", "date_inactivated"),
            },
        ),
        (
            "Contact Information",
            {
                "fields": (
                    "home_address",
                    "home_city",
                    "home_state",
                    "home_zip",
                    "home_phone",
                ),
            },
        ),
        (
            "System Information",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    # Bulk actions
    actions = ["make_active", "make_inactive", "mark_deceased"]

    def make_active(self, request, queryset):
        queryset.update(status="active", date_inactivated=None)
        self.message_user(request, f"{queryset.count()} members marked as active.")

    make_active.short_description = "Mark selected members as active"

    def make_inactive(self, request, queryset):
        from django.utils import timezone

        queryset.update(status="inactive", date_inactivated=timezone.now().date())
        self.message_user(request, f"{queryset.count()} members marked as inactive.")

    make_inactive.short_description = "Mark selected members as inactive"

    def mark_deceased(self, request, queryset):
        from django.utils import timezone

        queryset.update(status="deceased", date_inactivated=timezone.now().date())
        self.message_user(request, f"{queryset.count()} members marked as deceased.")

    mark_deceased.short_description = "Mark selected members as deceased"


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "member",
        "amount",
        "date",
        "payment_method",
        "receipt_number",
    ]
    list_filter = ["payment_method", "date"]
    search_fields = [
        "id",
        "member__first_name",
        "member__last_name",
        "member__member_id",
        "amount",
        "receipt_number",
    ]
    ordering = ["-date"]
    readonly_fields = ["id", "created_at", "updated_at"]
    date_hierarchy = "date"

    fieldsets = (
        (
            "Payment Information",
            {
                "fields": (
                    "id",
                    "member",
                    "amount",
                    "date",
                    "payment_method",
                    "receipt_number",
                ),
            },
        ),
        (
            "System Information",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )


# Register custom admin URL for deactivating expired members
# Monkey-patch admin site to add custom URL
original_get_urls = admin.site.get_urls


def custom_get_urls():
    urls = original_get_urls()
    custom_urls = [
        path(
            "deactivate-expired-members/",
            admin.site.admin_view(deactivate_expired_members_view),
            name="deactivate_expired_members",
        ),
    ]
    return custom_urls + urls


admin.site.get_urls = custom_get_urls
