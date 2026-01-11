from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required

def admin_required(view_func):
    """
    Only allows access to active staff users (admins).
    Non-admins are redirected to 'home' with a message.
    """
    @login_required(login_url='login')
    def wrapper(request, *args, **kwargs):
        if not request.user.is_active or not request.user.is_staff:
            messages.error(request, "Access denied. Admins only.")
            return redirect('home')  # redirect non-admins to home
        return view_func(request, *args, **kwargs)
    return wrapper


def lecturer_required(view_func):
    """
    Only allows access to active non-staff users (lecturers).
    Non-lecturers are redirected to 'dashboard' with a message.
    """
    @login_required(login_url='login')
    def wrapper(request, *args, **kwargs):
        if not request.user.is_active or request.user.is_staff:
            messages.error(request, "Access denied. Lecturers only.")
            return redirect('dashboard')  # redirect non-lecturers to admin dashboard
        return view_func(request, *args, **kwargs)
    return wrapper
