from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from analytics.models import Lecturer

def admin_required(view_func):
    """
    Only allows access to active staff users (admins).
    Requirements: is_active=True AND is_staff=True
    """
    @login_required(login_url='login')
    def wrapper(request, *args, **kwargs):
        if not request.user.is_active or not request.user.is_staff:
            messages.error(request, "Access denied. Admins only.")
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper


def lecturer_required(view_func):
    """
    Allows access to:
    1. Active staff users (admins) - auto-approved
    2. Active non-staff users with APPROVED Lecturer profile
    
    Redirects unapproved users to pending page.
    """
    @login_required(login_url='login')
    def wrapper(request, *args, **kwargs):
        # Check if user is active
        if not request.user.is_active:
            messages.error(request, "Your account has been deactivated.")
            return redirect('login')
        
        # ALLOW ADMINS - they can access lecturer views
        if request.user.is_staff:
            return view_func(request, *args, **kwargs)
        
        # FOR NON-STAFF (regular lecturers), check approval status
        try:
            lecturer = Lecturer.objects.get(user=request.user)
            
            # Check if approved
            if not lecturer.is_approved:
                messages.warning(request, "Your account is pending admin approval.")
                return redirect('pending_approval')
            
            # Approved - allow access
            return view_func(request, *args, **kwargs)
            
        except Lecturer.DoesNotExist:
            messages.error(
                request, 
                "No lecturer profile found. Please contact the administrator."
            )
            return redirect('login')
    
    return wrapper