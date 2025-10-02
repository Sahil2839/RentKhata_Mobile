from django.urls import path
from django.contrib.auth import views as auth_views
from . import views


urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name= 'signup'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path("tenant/dashboard/", views.tenant_dashboard, name="tenant_dashboard"),
    path("landlord/dashboard/", views.landlord_dashboard, name="landlord_dashboard"),
    path("guest/dashboard/", views.guest_dashboard, name="guest_dashboard"),
    path('landlord-request/', views.landlord_request, name='landlord_request'),
    path('manage-tenants/', views.manage_tenants, name='manage_tenants'),
    path("landlord/manage-tenants/", views.manage_tenants, name="manage_tenants"),
    path("landlord/delete-offline-tenant/<int:tenant_id>/", views.delete_offline_tenant, name="delete_offline_tenant"),
    path('delete-tenant-link/<int:link_id>/', views.delete_tenant_link, name='delete_tenant_link'),
    path('tenants/<int:tenant_id>/edit/', views.update_tenant, name='update_tenant'),
    path('tenant/invites/', views.tenant_invites, name='tenant_invites'),
    path("tenants/<int:tenant_id>/note/", views.update_tenant_note, name="update_tenant_note"), 
    path('bill/<int:tenant_id>/<str:tenant_type>/', views.view_bill, name='view_bill'),
    path('bill/<int:bill_id>/', views.bill_detail, name='bill_detail'),
    path('chat/', views.chat_view, name='chat'),
    path('chat/messages/<int:tenant_id>/', views.fetch_messages, name='fetch_messages'),
    path('chat/send/', views.send_message, name='send_message'),
    path('documents/', views.documents_dashboard, name='documents_dashboard'),
    path("documents/<int:tenant_id>/<str:tenant_type>/", views.tenant_documents, name="tenant_documents"),
    path("documents/delete/<int:doc_id>/", views.delete_document, name="delete_document"),
    path("bills/", views.all_bills, name="all_bills"),
    path('register-as-tenant/', views.register_as_tenant, name='register_as_tenant'),
    path('profile/', views.profile, name='profile'),
    path("password_change/",views.CustomPasswordChangeView.as_view(), name="password_change"),
    path('temp-create-superuser/', views.create_superuser_view),

]
