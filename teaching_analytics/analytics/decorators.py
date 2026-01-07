from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required


def admin_required(view_func):
    @login_required(login_url='login')
    def wrapper(request, *args, **kwargs):
        if not request.user.is_active or not request.user.is_staff:
            messages.error(request, "Access denied. Admins only.")
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper


def lecturer_required(view_func):
    @login_required(login_url='login')
    def wrapper(request, *args, **kwargs):
        if not request.user.is_active:
            messages.error(request, "Access denied. Lecturers only.")
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper
