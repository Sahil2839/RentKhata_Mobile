from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .forms import CustomUserCreationForm, CustomLogin
from .decorators import guest_required, landlord_required, tenant_required
from .models import CustomUser, LandlordRequest, OfflineTenants, LinkTenantLandlord, LinkRequest, Billing, ChatMessage, TenantDocument
from .forms import OfflineTenantForm, InviteTenantForm, OnlineTenantForm, TenantDocumentForm, ProfileForm
from datetime import date
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
from django.contrib.auth import get_user_model
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy


# Create your views here.
def home(request):
    return render(request, 'accounts/home.html')

def login_view(request):
    if request.method == 'POST':
        form = CustomLogin(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard')
    else:
        form = CustomLogin()
    return render(request, 'accounts/login.html', {'form': form})


def signup_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.save()
            login(request, user)
            return render(request, 'accounts/guest_dashboard.html')
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/signup.html', {'form': form})

@login_required
def dashboard(request):
    # reload fresh user role from DB
    user = request.user.__class__.objects.get(pk=request.user.pk)

    if user.role == 'guest':
        return redirect('guest_dashboard')
    elif user.role == 'landlord':
        return redirect('landlord_dashboard')
    elif user.role == 'tenant':
        return redirect('tenant_dashboard')

    return render(request, 'accounts/home.html')


@login_required
@tenant_required
def tenant_dashboard(request):
    return render(request, 'accounts/tenant_dashboard.html')

@login_required
@landlord_required
def landlord_dashboard(request):
    return render(request, 'accounts/landlord_dashboard.html')


@login_required
@guest_required
def guest_dashboard(request):
    message = request.session.pop('message', None)  # read and clear message
    return render(request, 'accounts/guest_dashboard.html', {"message": message})


@login_required
def landlord_request(request):
    user = CustomUser.objects.get(pk=request.user.pk)

    if request.method == 'POST':
        existing_request = LandlordRequest.objects.filter(user=user).first()

        if existing_request:
            # already requested → redirect with a message
            request.session['message'] = "You have already submitted a request. Please wait for approval."
        else:
            LandlordRequest.objects.create(user=user, status='pending')
            request.session['message'] = "Your request has been submitted successfully."

        # 🚀 Always redirect after POST to prevent 403 on reload
        return redirect('guest_dashboard')

    return redirect('guest_dashboard')


@login_required
@landlord_required
def manage_tenants(request):
    landlord = request.user

    # --- Offline Tenant Form ---
    offline_form = OfflineTenantForm()
    if request.method == "POST" and "add_offline" in request.POST:
        offline_form = OfflineTenantForm(request.POST)
        if offline_form.is_valid():
            offline_tenant = offline_form.save(commit=False)
            offline_tenant.landlord = landlord
            offline_tenant.save()
            messages.success(request, "Offline tenant added successfully.")
            return redirect("manage_tenants")
        else:
            messages.error(request, "Please fix the errors in the offline tenant form.")

    # --- Invite Tenant Form ---
    invite_form = InviteTenantForm()
    if request.method == "POST" and "invite_tenant" in request.POST:
        invite_form = InviteTenantForm(request.POST)
        if invite_form.is_valid():
            username_or_phone = invite_form.cleaned_data["username_or_phone"]
            property_name = invite_form.cleaned_data.get("property_name")
            rent = invite_form.cleaned_data.get("rent") or 0
            due_amount = invite_form.cleaned_data.get("due_amount") or 0
            meter_rate = invite_form.cleaned_data.get("meter_rate") or 10
            starting_meter_reading = invite_form.cleaned_data.get("starting_meter_reading") or 0
            start_date = invite_form.cleaned_data.get("start_date")
            end_date = invite_form.cleaned_data.get("end_date")
            note = invite_form.cleaned_data.get("note")

            try:
                tenant_user = CustomUser.objects.get(
                    Q(username=username_or_phone) | Q(phone_number=username_or_phone),
                    
                )

                existing_invite = LinkRequest.objects.filter(
                    sender=landlord,
                    receiver=tenant_user,
                    status='pending'
                ).first()

                if existing_invite:
                    messages.info(request, f"An invite is already pending for {tenant_user.username}.")
                else:
                    LinkRequest.objects.create(
                        sender=landlord,
                        receiver=tenant_user,
                        status='pending',
                        property_name=property_name or "",
                        rent=rent,
                        meter_rate=meter_rate,
                        starting_meter_reading=starting_meter_reading,
                        start_date=start_date,
                        end_date=end_date,
                        due_amount=due_amount,
                        note=note or ""
                    )
                    messages.success(request, f"Invite sent to {tenant_user.username}.")

            except CustomUser.DoesNotExist:
                messages.error(request, "No tenant exists with this username or phone number.")

            return redirect("manage_tenants")

    # --- Prepare tenants for display ---
    query = request.GET.get("q", "")
    due_filter = request.GET.get("due_filter", "")

    tenants = []

    # --- Offline tenants ---
    offline_tenants = OfflineTenants.objects.filter(landlord=landlord)
    if query:
        offline_tenants = offline_tenants.filter(
            Q(name__icontains=query) | Q(phone_number__icontains=query)
        )

    for t in offline_tenants:
        latest_bill = t.offline_bill.order_by('-created_at').first()

        if latest_bill:
            # Dynamic due calculation
            prev_due = latest_bill.previous_due_amount or 0
            rent = latest_bill.rent or 0
            meter_rate = latest_bill.meter_rate or 10
            prev_meter = latest_bill.previous_meter_reading or 0
            curr_meter = latest_bill.current_meter_reading if latest_bill.current_meter_reading is not None else prev_meter
            meter_amount = (curr_meter - prev_meter) * meter_rate
            misc = latest_bill.misc_charge or 0
            paid = latest_bill.amount_paid or 0

            due_amount = prev_due + rent + meter_amount + misc - paid
            latest_meter = curr_meter
        else:
            due_amount = t.due_amount or 0
            latest_meter = t.starting_meter_reading or 0

        tenants.append({
            'id': t.id,
            'type_label': 'Offline',
            'status': 'active',
            'name': t.name,
            'phone_number': t.phone_number,
            'property_name': t.property_name,
            'rent': t.rent,
            'due_amount': due_amount,
            'latest_meter': latest_meter,
            'start_date': t.start_date,
            'end_date': t.end_date,
            'note': t.note,
            'is_online': False,
            'tenant_obj': None,
            'pending_invite': False,
        })

    # --- Online tenants ---
    online_links = LinkTenantLandlord.objects.filter(landlord=landlord)
    if query:
        online_links = online_links.filter(
            Q(tenant__username__icontains=query) | Q(tenant__phone_number__icontains=query)
        )

    for link in online_links:
        latest_bill = link.online_bill.order_by('-created_at').first()

        if latest_bill:
            # Dynamic due calculation
            prev_due = latest_bill.previous_due_amount or 0
            rent = latest_bill.rent or 0
            meter_rate = latest_bill.meter_rate or 10
            prev_meter = latest_bill.previous_meter_reading or 0
            curr_meter = latest_bill.current_meter_reading if latest_bill.current_meter_reading is not None else prev_meter
            meter_amount = (curr_meter - prev_meter) * meter_rate
            misc = latest_bill.misc_charge or 0
            paid = latest_bill.amount_paid or 0

            due_amount = prev_due + rent + meter_amount + misc - paid
            latest_meter = curr_meter
        else:
            due_amount = link.due_amount or 0
            latest_meter = link.starting_meter_reading or 0

        tenants.append({
            'id': link.id,
            'type_label': 'Online',
            'status': 'active',
            'name': link.tenant.get_full_name() or link.tenant.username,
            'phone_number': link.tenant.phone_number,
            'property_name': link.property_name,
            'rent': link.rent,
            'due_amount': due_amount,
            'latest_meter': latest_meter,
            'start_date': link.start_date,
            'end_date': link.end_date,
            'note': link.note,
            'is_online': True,
            'tenant_obj': link.tenant,
            'pending_invite': False,
        })

    # --- Pending invites ---
    pending_invites = LinkRequest.objects.filter(sender=landlord, status='pending')
    if query:
        pending_invites = pending_invites.filter(
            Q(receiver__username__icontains=query) | Q(receiver__phone_number__icontains=query)
        )
    for invite in pending_invites:
        tenants.append({
            'id': invite.id,
            'type_label': 'Online',
            'status': 'pending',
            'name': invite.receiver.get_full_name() or invite.receiver.username,
            'phone_number': invite.receiver.phone_number,
            'property_name': invite.property_name,
            'rent': invite.rent or 0,
            'due_amount': invite.due_amount or 0,
            'latest_meter': invite.starting_meter_reading or 0,
            'start_date': invite.start_date,
            'end_date': invite.end_date,
            'note': '',
            'is_online': True,
            'tenant_obj': invite.receiver,
            'pending_invite': True,
        })

    # --- Sort and filter ---
    tenants.sort(key=lambda x: x['name'].lower() if x['name'] else "")
    if due_filter == "pending":
        tenants = [t for t in tenants if t['due_amount'] > 0]
    elif due_filter == "extra":
        tenants = [t for t in tenants if t['due_amount'] < 0]
    elif due_filter == "clear":
        tenants = [t for t in tenants if t['due_amount'] == 0]

    context = {
        "tenants": tenants,
        "offline_form": offline_form,
        "invite_form": invite_form,
        "query": query,
        "due_filter": due_filter,
        "show_username": request.GET.get("show_username", "0"),
    }

    return render(request, "accounts/manage_tenants.html", context)



@login_required
@tenant_required
def tenant_invites(request):
    # Get all pending invites for this tenant
    invites = LinkRequest.objects.filter(receiver=request.user, status='pending')

    if request.method == "POST":
        invite_id = request.POST.get("invite_id")
        action = request.POST.get("action")  # 'accept' or 'reject'
        invite = get_object_or_404(LinkRequest, id=invite_id, receiver=request.user, status='pending')

        if action == 'accept':
            invite.status = 'accepted'
            invite.save()

            # Create a tenant-landlord link only when accepted
            LinkTenantLandlord.objects.get_or_create(
                landlord=invite.sender,
                tenant=invite.receiver,
                defaults={
                    "property_name": invite.property_name or "",
                    "rent": invite.rent or 0,
                    "due_amount": invite.due_amount or 0,
                    "meter_rate": invite.meter_rate or 0,
                    "starting_meter_reading": invite.starting_meter_reading or 0,
                    "previous_meter_reading": invite.starting_meter_reading or 0,
                    "current_meter_reading": invite.starting_meter_reading or 0,
                    "start_date": invite.start_date,
                    "end_date": invite.end_date,
                    "note": invite.note or ""
                }
            )
            messages.success(request, f"Invite from {invite.sender.username} approved.")

        elif action == 'reject':
            invite.status = 'rejected'
            invite.save()
            messages.info(request, f"Invite from {invite.sender.username} rejected.")

        return redirect('tenant_invites')

    return render(request, "accounts/tenant_invites.html", {"invites": invites})


@login_required
@landlord_required
def delete_offline_tenant(request, tenant_id):
    tenant = get_object_or_404(OfflineTenants, id=tenant_id, landlord=request.user)
    tenant.delete()
    return redirect('manage_tenants')


@login_required
@landlord_required
def delete_tenant_link(request, link_id):
    link = get_object_or_404(LinkTenantLandlord, id=link_id, landlord=request.user)
    link.delete()

    # Delete corresponding LinkRequest
    LinkRequest.objects.filter(
        sender=request.user,
        receiver=link.tenant,
        status='accepted'
    ).delete()

    return redirect('manage_tenants')


@login_required
@landlord_required
def update_tenant_note(request, tenant_id):
    # Try to get online tenant first
    tenant_obj = None
    is_online = True
    try:
        tenant_obj = LinkTenantLandlord.objects.get(id=tenant_id, landlord=request.user)
    except LinkTenantLandlord.DoesNotExist:
        tenant_obj = get_object_or_404(OfflineTenants, id=tenant_id, landlord=request.user)
        is_online = False

    if request.method == "POST":
        note = request.POST.get("note", "").strip()
        tenant_obj.note = note
        tenant_obj.save()

        tenant_name = tenant_obj.tenant.username if is_online else tenant_obj.name
        messages.success(request, f"Note updated for {tenant_name}")

    return redirect("manage_tenants")


@login_required
@landlord_required
def update_tenant(request, tenant_id):
    landlord = request.user

    # Try offline tenant first
    try:
        tenant = OfflineTenants.objects.get(id=tenant_id, landlord=landlord)
        tenant_type = "offline"
    except OfflineTenants.DoesNotExist:
        tenant = get_object_or_404(LinkTenantLandlord, id=tenant_id, landlord=landlord)
        tenant_type = "online"

    if request.method == "POST":
        if tenant_type == "offline":
            form = OfflineTenantForm(request.POST, instance=tenant)
        else:
            form = OnlineTenantForm(request.POST, instance=tenant)

        if form.is_valid():
            form.save()
            messages.success(request, "Tenant updated successfully.")
            return redirect("manage_tenants")
    else:
        if tenant_type == "offline":
            form = OfflineTenantForm(instance=tenant)
        else:
            form = OnlineTenantForm(instance=tenant)

    return render(request, "accounts/update_tenant.html", {
        "form": form,
        "tenant_type": tenant_type,
    })



@login_required
@landlord_required
def view_bill(request, tenant_id, tenant_type):
    if tenant_type == "Offline":
        tenant = get_object_or_404(OfflineTenants, id=tenant_id)
        bills_qs = tenant.offline_bill.all().order_by('-created_at')
        last_meter = bills_qs.first().current_meter_reading if bills_qs.exists() else tenant.starting_meter_reading
        last_due = bills_qs.first().remaining_due_amount if bills_qs.exists() else tenant.due_amount
    elif tenant_type == "Online":
        link = get_object_or_404(LinkTenantLandlord, id=tenant_id)
        tenant = link
        bills_qs = link.online_bill.all().order_by('-created_at')
        last_meter = bills_qs.first().current_meter_reading if bills_qs.exists() else link.starting_meter_reading
        last_due = bills_qs.first().remaining_due_amount if bills_qs.exists() else link.due_amount
    else:
        messages.error(request, "Invalid tenant type.")
        return redirect("manage_tenants")

    if request.method == "POST" and "generate_bill" in request.POST:
        rent = int(request.POST.get("rent", tenant.rent))
        meter_rate = int(request.POST.get("meter_rate", getattr(tenant, "meter_rate", 10)))
        new_bill = Billing.objects.create(
            offline_tenant=tenant if tenant_type == "Offline" else None,
            online_tenant=tenant if tenant_type == "Online" else None,
            rent=rent,
            previous_due_amount=last_due,
            meter_rate=meter_rate,
            starting_meter_reading=tenant.starting_meter_reading or 0,
            previous_meter_reading=last_meter,
            current_meter_reading=last_meter,
            amount_paid=0,
            start_date=date.today().replace(day=1),
            end_date=date.today()
        )
        messages.success(request, "New bill created.")
        return redirect("view_bill", tenant_id=tenant_id, tenant_type=tenant_type)

    context = {
        "tenant": tenant,
        "bills": bills_qs,
        "tenant_type": tenant_type,
        "last_meter": last_meter,
    }
    return render(request, "accounts/view_bill.html", context)



@login_required
def bill_detail(request, bill_id):
    bill = get_object_or_404(Billing, id=bill_id)

    tenant = bill.offline_tenant or bill.online_tenant
    tenant_name = bill.offline_tenant.name if bill.offline_tenant else bill.online_tenant.tenant.username

    if bill.current_meter_reading is None:
        bill.current_meter_reading = bill.previous_meter_reading or 0
        bill.save()

    if request.method == "POST":
        meter = request.POST.get("current_meter_reading")
        misc = request.POST.get("misc_charge")
        note = request.POST.get("misc_note")
        paid = request.POST.get("amount_paid")

        # ✅ Handle meter photo upload
        if "meter_photo" in request.FILES:
            bill.meter_photo = request.FILES["meter_photo"]

        # ✅ Handle remove photo checkbox
        if request.POST.get("remove_photo"):
            bill.meter_photo.delete(save=False)  # delete file from storage
            bill.meter_photo = None

        if meter is not None and meter != "":
            bill.current_meter_reading = int(meter)
        if misc is not None and misc != "":
            bill.misc_charge = int(misc)
        if note is not None:
            bill.misc_note = note
        if paid is not None and paid != "":
            bill.amount_paid = int(paid)

        # Recalculate current bill
        bill.consumption_units = bill.current_meter_reading - bill.previous_meter_reading
        bill.meter_bill_amount = bill.consumption_units * bill.meter_rate
        total_amount = bill.rent + (bill.previous_due_amount or 0) + bill.meter_bill_amount + (bill.misc_charge or 0)
        remaining_due = total_amount - (bill.amount_paid or 0)  # allow negative

        bill.remaining_due_amount = remaining_due

        # Status
        if remaining_due <= 0:
            bill.status = 'paid'
        elif bill.amount_paid and bill.amount_paid < total_amount:
            bill.status = 'partial'
        else:
            bill.status = 'unpaid'
        bill.save()

        # --- Recalculate all subsequent bills ---
        subsequent_bills = Billing.objects.filter(
            offline_tenant=bill.offline_tenant if bill.offline_tenant else None,
            online_tenant=bill.online_tenant if bill.online_tenant else None,
            start_date__gt=bill.start_date
        ).order_by('start_date')

        prev_meter = bill.current_meter_reading
        prev_due = remaining_due

        for b in subsequent_bills:
            b.previous_meter_reading = prev_meter
            if b.current_meter_reading is None or b.current_meter_reading < prev_meter:
                b.current_meter_reading = prev_meter  # avoid negative consumption
            b.previous_due_amount = prev_due

            b.consumption_units = b.current_meter_reading - b.previous_meter_reading
            b.meter_bill_amount = b.consumption_units * b.meter_rate

            total_amount_b = b.rent + (b.previous_due_amount or 0) + b.meter_bill_amount + (b.misc_charge or 0)
            remaining_due_b = total_amount_b - (b.amount_paid or 0)

            b.remaining_due_amount = remaining_due_b

            if remaining_due_b <= 0:
                b.status = 'paid'
            elif b.amount_paid and b.amount_paid < total_amount_b:
                b.status = 'partial'
            else:
                b.status = 'unpaid'

            b.save()
            prev_meter = b.current_meter_reading
            prev_due = remaining_due_b

        messages.success(request, "Bill and subsequent bills updated successfully.")
        return redirect("bill_detail", bill_id=bill.id)

    # For template display
    consumption_units = bill.current_meter_reading - bill.previous_meter_reading
    meter_bill_amount = consumption_units * bill.meter_rate
    total_amount = bill.rent + (bill.previous_due_amount or 0) + meter_bill_amount + (bill.misc_charge or 0)
    remaining_due = total_amount - (bill.amount_paid or 0)

    context = {
        "bill": bill,
        "tenant_name": tenant_name,
        "previous_meter": bill.previous_meter_reading or 0,
        "consumption_units": consumption_units,
        "meter_bill_amount": meter_bill_amount,
        "total_amount": total_amount,
        "remaining_due": remaining_due,
    }

    return render(request, "accounts/bill_detail.html", context)




User = get_user_model()

@login_required
def chat_view(request):
    user = request.user
    tenants = []

    if user.role == "landlord":
        # Only online tenants linked to this landlord
        links = LinkTenantLandlord.objects.filter(landlord=user)
        tenants = [link.tenant for link in links]  # list of User objects

    elif user.role == "tenant":
        # Tenant can chat with linked landlords only
        links = LinkTenantLandlord.objects.filter(tenant=user)
        tenants = [link.landlord for link in links]

    return render(request, 'accounts/chat.html', {'tenants': tenants})

@login_required
def fetch_messages(request, tenant_id):
    user = request.user
    tenant = get_object_or_404(User, id=tenant_id)

    messages = ChatMessage.objects.filter(
        sender__in=[user, tenant],
        receiver__in=[user, tenant]
    ).order_by('timestamp')

    data = [
        {
            'sender': msg.sender.username,
            'receiver': msg.receiver.username,
            'message': msg.message,
            'timestamp': msg.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        } for msg in messages
    ]
    return JsonResponse({'messages': data})


@login_required
def send_message(request):
    if request.method == "POST":
        sender = request.user
        receiver_id = request.POST.get('receiver_id')
        message = request.POST.get('message')
        receiver = get_object_or_404(User, id=receiver_id)
        msg = ChatMessage.objects.create(sender=sender, receiver=receiver, message=message)

        return JsonResponse({
            'sender': msg.sender.username,
            'message': msg.message,
            'timestamp': msg.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        })
    

@login_required
def documents_dashboard(request):
    # Offline tenants added by this landlord
    offline_tenants = OfflineTenants.objects.filter(landlord=request.user)

    # Online tenants linked to this landlord
    linked_tenants = LinkTenantLandlord.objects.filter(landlord=request.user)
    online_tenants = [link.tenant for link in linked_tenants]

    return render(request, "accounts/documents_dashboard.html", {
        'offline_tenants': offline_tenants,
        'online_tenants': online_tenants
    })


@login_required
@landlord_required
def tenant_documents(request, tenant_id, tenant_type):
    if tenant_type == "offline":
        tenant = get_object_or_404(OfflineTenants, id=tenant_id, landlord=request.user)
        documents = TenantDocument.objects.filter(offline_tenant=tenant, tenant_type="offline")
    else:  # online
        link = get_object_or_404(LinkTenantLandlord, tenant_id=tenant_id, landlord=request.user)
        tenant = link.tenant
        documents = TenantDocument.objects.filter(online_tenant=tenant, tenant_type="online")

    if request.method == "POST":
        form = TenantDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.tenant_type = tenant_type
            if tenant_type == "offline":
                doc.offline_tenant = tenant
            else:
                doc.online_tenant = tenant
            doc.save()
            return redirect("tenant_documents", tenant_id=tenant_id, tenant_type=tenant_type)
    else:
        form = TenantDocumentForm()

    return render(request, "accounts/tenant_documents.html", {
        "tenant": tenant,
        "documents": documents,
        "form": form,
        "tenant_type": tenant_type,
    })


@login_required
@landlord_required
def delete_document(request, doc_id):
    doc = get_object_or_404(TenantDocument, id=doc_id)

    # Check permissions: landlord can delete
    if doc.tenant_type == "offline":
        if doc.offline_tenant.landlord != request.user:
            return HttpResponseForbidden("Not allowed")
        tenant_id = doc.offline_tenant.id
        tenant_type = "offline"
    else:  # online tenant
        link_exists = LinkTenantLandlord.objects.filter(
            tenant=doc.online_tenant, landlord=request.user
        ).exists()
        if not link_exists:
            return HttpResponseForbidden("Not allowed")
        tenant_id = doc.online_tenant.id
        tenant_type = "online"

    doc.delete()
    return redirect("tenant_documents", tenant_id=tenant_id, tenant_type=tenant_type)


@login_required
def all_bills(request):
    user = request.user
    tenants_filter = request.GET.get("tenant", "")
    bills = Billing.objects.none()  # default empty queryset

    if user.role == "landlord":
        # Offline tenants
        offline_tenants = OfflineTenants.objects.filter(landlord=user)
        # Online tenants (links)
        links = LinkTenantLandlord.objects.filter(landlord=user)

        # Filter bills
        bills = Billing.objects.filter(
            Q(offline_tenant__in=offline_tenants) |
            Q(online_tenant__in=links)
        )

        # Optional filter by tenant name
        if tenants_filter:
            bills = bills.filter(
                Q(offline_tenant__name__icontains=tenants_filter) |
                Q(online_tenant__tenant__username__icontains=tenants_filter)
            )

        bills = bills.order_by("-start_date")

    elif user.role == "tenant":
        # Only show bills linked to this tenant
        # Online tenant bills
        links = LinkTenantLandlord.objects.filter(tenant=user)
        bills = Billing.objects.filter(
            Q(online_tenant__in=links)
        ).order_by("-start_date")

    return render(request, "accounts/all_bills.html", {
        "bills": bills,
        "tenants_filter": tenants_filter,
    })


@login_required
def register_as_tenant(request):
    user = request.user

    if user.role != "guest":
        messages.warning(request, "You are already registered as a tenant or have another role.")
        return redirect("tenant_dashboard")  

    # Promote guest to tenant
    user.role = "tenant"
    user.save()

    messages.success(request, "You have been registered as a tenant!")
    return redirect("tenant_dashboard")


@login_required
def profile(request):
    user = request.user
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('profile')
    else:
        form = ProfileForm(instance=user)

    return render(request, "accounts/profile.html", {"form": form})


class CustomPasswordChangeView(PasswordChangeView):
    template_name = "accounts/password_change.html"

    def get_success_url(self):
        messages.success(self.request, "Password changed successfully ✅")
        return reverse_lazy("profile")
    
