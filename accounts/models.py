from django.db import models
from django.contrib.auth.models import AbstractUser 
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.utils import timezone

# Create your models here.
    
class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('guest', 'Guest'),
        ('landlord', 'Landlord'),
        ('tenant', 'Tenant'),
    )
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='guest'
    )
    username = models.CharField(max_length=20, unique=True, null=False, blank=False)
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    
    USERNAME_FIELD = 'username'

    

class LinkTenantLandlord(models.Model):
    tenant = models.ForeignKey(
        CustomUser,
        related_name='landlord_link',
        limit_choices_to={'role': 'tenant'},
        on_delete=models.CASCADE
    )
    landlord = models.ForeignKey(
        CustomUser,
        related_name='tenant_link',
        limit_choices_to={'role': 'landlord'},
        on_delete=models.CASCADE
    )
    property_name = models.CharField(max_length=255)
    rent = models.IntegerField()
    due_amount = models.IntegerField(default=0)
    meter_rate = models.IntegerField(default=0)
    starting_meter_reading = models.IntegerField(default=0)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    note = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.tenant.username} - tenant of {self.landlord.username}"
    

class LinkRequest(models.Model):
    sender = models.ForeignKey(CustomUser, related_name='sent_requests', on_delete=models.CASCADE)
    receiver = models.ForeignKey(CustomUser, related_name='received_requests', on_delete=models.CASCADE)

    REQUEST_STATUS = (
        ('not_initiated', 'Not Initiated'),
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    )

    status = models.CharField(max_length=15, choices=REQUEST_STATUS, default='not_initiated')

    # new fields
    property_name = models.CharField(max_length=255, blank=True, null=True)
    rent = models.IntegerField(blank=True, null=True, default=0)
    due_amount = models.IntegerField(blank=True, null=True, default=0)
    meter_rate = models.IntegerField(blank=False, null=False, default=0)
    starting_meter_reading = models.IntegerField(blank=True, null=True, default=0)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.sender.username} → {self.receiver.username} ({self.status})'

    def save(self, *args, **kwargs):
        creating = self.pk is None
        old_status = None
        if not creating:
            old_status = LinkRequest.objects.get(pk=self.pk).status

        super().save(*args, **kwargs)

        # when tenant accepts → create link with landlord details
        if self.status == 'accepted' and old_status != 'accepted':
            from .models import LinkTenantLandlord
            LinkTenantLandlord.objects.get_or_create(
                landlord=self.sender,
                tenant=self.receiver,
                defaults={
                    "property_name": self.property_name or "",
                    "rent": self.rent or 0,
                    "due_amount": self.due_amount or 0,
                    "meter_rate": self.meter_rate or 0,
                    "starting_meter_reading": self.starting_meter_reading or 0,
                    "start_date": self.start_date,
                    "end_date": self.end_date,
                }
            )


class LandlordRequest(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    request_status = (
        ('not_initiated', 'Not Initiated'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    status = models.CharField(
        max_length=15,
        choices=request_status,
        default='not_initiated'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s request status: {self.status}"
    

# ------------------ Offline Tenants ------------------
class OfflineTenants(models.Model):
    landlord = models.ForeignKey(
        CustomUser,
        related_name='offline_tenants',
        limit_choices_to={'role': 'landlord'},
        on_delete=models.CASCADE
    )
    name = models.CharField(max_length=20)
    property_name = models.CharField(max_length=255, null=True, blank=True)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    rent = models.IntegerField()
    due_amount = models.IntegerField(default=0)
    meter_rate = models.IntegerField(default=10)
    starting_meter_reading = models.IntegerField(default=0)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    note = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name
    
   
# ------------------ Billing ------------------
class Billing(models.Model):
    online_tenant = models.ForeignKey(
        'LinkTenantLandlord', related_name='online_bill',
        null=True, blank=True, on_delete=models.CASCADE
    )
    offline_tenant = models.ForeignKey(
        'OfflineTenants', related_name='offline_bill',
        null=True, blank=True, on_delete=models.CASCADE
    )

    start_date = models.DateField()
    end_date = models.DateField()

    rent = models.IntegerField()
    previous_due_amount = models.IntegerField(default=0)
    total_amount = models.IntegerField(null=True, blank=True)
    amount_paid = models.IntegerField(default=0)
    remaining_due_amount = models.IntegerField(null=True, blank=True)
    

   
    # starting_meter_reading = models.IntegerField(default=0)
    previous_meter_reading = models.IntegerField(default=0)
    current_meter_reading = models.IntegerField(null=True, blank=True)
    meter_photo = models.ImageField(upload_to='meter_photos/', null=True, blank=True)
    meter_rate = models.IntegerField(default=0)

    misc_charge = models.IntegerField(default=0)
    misc_note = models.TextField(null=True, blank=True)

    STATUS_CHOICES = [
        ('unpaid', 'Unpaid'),
        ('partial', 'Partial'),
        ('paid', 'Paid'),
    ]
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='unpaid')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ------------------ Validation ------------------
    def clean(self):
        if not self.online_tenant and not self.offline_tenant:
            raise ValidationError("Either online_tenant or offline_tenant must be set.")
        if self.online_tenant and self.offline_tenant:
            raise ValidationError("Only one of online_tenant or offline_tenant should be set.")

    # ------------------ Computed Properties ------------------
    @property
    def consumption(self):
        if self.current_meter_reading is None:
            return 0
        return max(0, (self.current_meter_reading - self.previous_meter_reading))

    @property
    def meter_bill(self):
        return self.consumption * (self.meter_rate or 0)

    @property
    def total_bill_amount(self):
        return (self.rent or 0) + (self.previous_due_amount or 0) + (self.meter_bill or 0) + (self.misc_charge or 0)

    @property
    def remaining_due(self):
        return self.total_bill_amount - (self.amount_paid or 0)

    # ------------------ Status Update ------------------
    def save(self, *args, **kwargs):
    # Set current_meter_reading for new bills if not provided
        if not self.pk and self.current_meter_reading is None:
            self.current_meter_reading = self.previous_meter_reading or 0

        # Always recalculate total_amount
        self.total_amount = (
            (self.rent or 0)
            + (self.previous_due_amount or 0)
            + ((self.current_meter_reading or 0) - (self.previous_meter_reading or 0)) * (self.meter_rate or 0)
            + (self.misc_charge or 0)
        )

        # Always recalculate remaining due
        self.remaining_due_amount = self.total_amount - (self.amount_paid or 0)

        # Update status based on remaining due
        if self.remaining_due_amount <= 0:
            self.status = 'paid'
        elif self.amount_paid and self.amount_paid < self.total_amount:
            self.status = 'partial'
        else:
            self.status = 'unpaid'

        super().save(*args, **kwargs)

    # ------------------ String Representation ------------------
    def __str__(self):
        if self.online_tenant:
            return f"Bill for {self.online_tenant.tenant.username}"
        elif self.offline_tenant:
            return f"Bill for {self.offline_tenant.name}"
        return "Unassigned Bill"
    

User = get_user_model()

class ChatMessage(models.Model):
    sender = models.ForeignKey(User, related_name='sent_messages', on_delete=models.CASCADE)
    receiver = models.ForeignKey(User, related_name='received_messages', on_delete=models.CASCADE)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.sender.username} → {self.receiver.username} : {self.message[:20]}"
    

class TenantDocument(models.Model):
    TENANT_TYPES = [("offline", "Offline"), ("online", "Online")]
    tenant_type = models.CharField(max_length=10, choices=TENANT_TYPES)
    offline_tenant = models.ForeignKey('OfflineTenants', on_delete=models.CASCADE, blank=True, null=True)
    online_tenant = models.ForeignKey(CustomUser, on_delete=models.CASCADE, blank=True, null=True)
    document_name = models.CharField(max_length=200)
    file = models.FileField(upload_to="tenant_documents/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.document_name