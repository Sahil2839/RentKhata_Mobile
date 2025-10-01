from django.contrib import admin
from .models import CustomUser, LinkTenantLandlord, LinkRequest, OfflineTenants, Billing, LandlordRequest


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'role', 'phone_number', 'email')
    list_filter = ('role',)
    search_fields = ('username', 'email', 'phone_number')

    def delete_model(self, request, obj):
        # Block deleting superusers
        if obj.is_superuser:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("Superusers cannot be deleted from admin!")

        # Extra safety: block deleting yourself
        if obj == request.user:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("You cannot delete your own account!")

        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        # Block bulk deleting superusers
        if queryset.filter(is_superuser=True).exists():
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("You cannot delete superusers in bulk!")

        # Block if your own account is in bulk selection
        if queryset.filter(pk=request.user.pk).exists():
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("You cannot bulk delete your own account!")

        super().delete_queryset(request, queryset)


@admin.register(LinkTenantLandlord)
class LinkTenantLandlordAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'landlord', 'property_name', 'rent', 'due_amount')
    list_filter = ('start_date', 'end_date')
    search_fields = ('property_name', 'tenant__username', 'landlord__username')


@admin.register(LinkRequest)
class LinkRequestAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'status', 'created_at', 'updated_at')
    list_filter = ('status',)
    search_fields = ('sender__username', 'receiver__username')


@admin.register(OfflineTenants)
class OfflineTenantAdmin(admin.ModelAdmin):
    list_display = ('name', 'landlord', 'property_name', 'rent', 'due_amount')
    search_fields = ('name', 'property_name', 'landlord__username')


@admin.register(Billing)
class BillingAdmin(admin.ModelAdmin):
    list_display = (
        "get_tenant", 
        "start_date", 
        "end_date",  
        "total_bill_amount", 
        "amount_paid", 
        "remaining_due", 
        "status"
    )
    search_fields = ("online_tenant__tenant__username", "offline_tenant__name")
    list_filter = ("status", "start_date", "end_date")

    def remaining_due(self, obj):
        return obj.remaining_due

    def get_tenant(self, obj):
        if obj.online_tenant:
            return obj.online_tenant.tenant.username  # adjust if you store differently
        elif obj.offline_tenant:
            return obj.offline_tenant.name
        return "-"
    get_tenant.short_description = "Tenant"  # Column header in admin



@admin.register(LandlordRequest)
class LandlordRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'created_at', 'updated_at')
    search_fields = ('user__username',)
    list_filter = ('status', 'created_at', 'updated_at')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # if approved, update user role
        if obj.status == 'approved':
            obj.user.role = 'landlord'
            obj.user.save()
