from django.shortcuts import redirect
from functools import wraps

def role_required(required_role):
    """General purpose decorator for checking user role, superusers bypass"""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')   # not logged in → go to login page
            
            # Superuser bypass
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            # Role check
            if request.user.role != required_role:
                # Redirect them to their correct dashboard
                if request.user.role == 'tenant':
                    return redirect('tenant_dashboard')
                elif request.user.role == 'landlord':
                    return redirect('landlord_dashboard')
                elif request.user.role == 'guest':
                    return redirect('guest_dashboard')
                else:
                    return redirect('home')  # fallback

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

# Shortcuts for specific roles
def guest_required(view_func):
    return role_required('guest')(view_func)

def landlord_required(view_func):
    return role_required('landlord')(view_func)

def tenant_required(view_func):
    return role_required('tenant')(view_func)
