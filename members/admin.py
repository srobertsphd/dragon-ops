from django.contrib import admin
from django.utils.html import format_html
from .models import Member, MemberType, PaymentMethod, Payment


@admin.register(MemberType)
class MemberTypeAdmin(admin.ModelAdmin):
    list_display = [
        "member_type_id",
        "name",
        "monthly_dues",
        "coverage_months",
        "is_active",
    ]
    list_filter = ["is_active"]
    search_fields = ["name"]
    ordering = ["name"]


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ["payment_method_id", "name", "is_credit_card", "is_active"]
    list_filter = ["is_credit_card", "is_active"]
    search_fields = ["name"]
    ordering = ["name"]


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = [
        "member_id",
        "first_name",
        "last_name",
        "member_type",
        "status",
        "expiration_date",
        "home_phone",
    ]
    list_filter = ["member_type", "status", "home_country"]
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
                    "home_country",
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
        "payment_id",
        "member",
        "amount",
        "date",
        "payment_method",
        "receipt_number",
    ]
    list_filter = ["payment_method", "date"]
    search_fields = [
        "payment_id",
        "member__first_name",
        "member__last_name",
        "member__member_id",
        "amount",
        "receipt_number",
    ]
    ordering = ["-date"]
    readonly_fields = ["created_at", "updated_at"]
    date_hierarchy = "date"

    fieldsets = (
        (
            "Payment Information",
            {
                "fields": (
                    "payment_id",
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
