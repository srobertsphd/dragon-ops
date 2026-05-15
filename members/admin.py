from django.contrib import admin
from django import forms
from django.db import models
from django.contrib.auth.views import LoginView
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.utils.http import url_has_allowed_host_and_scheme
from .models import Member, MemberType, PaymentMethod, Payment


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
        css = {"all": ("members/css/admin_member_id_width.css",)}

    list_display = [
        "member_id",
        "first_name",
        "last_name",
        "member_type",
        "status",
        "date_joined",
        "expiration_date",
        "home_phone",
    ]
    list_filter = ["member_type", "status", "home_state", "date_joined"]
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
        "member",
        "amount",
        "date",
        "payment_method",
        "receipt_number",
        "new_expiration_date",
    ]
    list_filter = ["payment_method", "date"]
    search_fields = [
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
                    "member",
                    "amount",
                    "date",
                    "payment_method",
                    "receipt_number",
                    "new_expiration_date",
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


# Override admin login to redirect to main app instead of /admin/


class CustomAdminLoginView(LoginView):
    """Custom admin login view that redirects to main app after login"""

    template_name = "admin/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        # Check if there's a 'next' parameter (user requested specific redirect)
        redirect_to = self.request.GET.get(REDIRECT_FIELD_NAME, "")
        if redirect_to:
            # Validate the redirect URL is safe
            if url_has_allowed_host_and_scheme(
                url=redirect_to,
                allowed_hosts={self.request.get_host()},
                require_https=self.request.is_secure(),
            ):
                return redirect_to

        # Default: redirect to main app instead of /admin/
        return "/"


# Store original login method
original_admin_login = admin.site.login


# Override admin site's login method
def custom_admin_login(request, extra_context=None):
    """Custom admin login that uses our custom login view with admin template"""
    if extra_context is None:
        extra_context = {}
    # Use admin site's default extra_context
    extra_context.update(admin.site.each_context(request))
    return CustomAdminLoginView.as_view(extra_context=extra_context)(request)


# Replace admin site's login method
admin.site.login = custom_admin_login
