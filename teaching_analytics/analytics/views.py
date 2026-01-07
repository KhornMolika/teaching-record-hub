from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required


# Custom decorators for role-based access control
def admin_required(view_func):
    @login_required(login_url='login')
    def wrapper(request, *args, **kwargs):
        if not request.user.is_active or not request.user.is_staff:
            messages.error(request, "Access denied. Admins only.")
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


def lecturer_required(view_func):
    @login_required(login_url='login')
    def wrapper(request, *args, **kwargs):
        if not request.user.is_active or request.user.is_staff:
            messages.error(request, "Access denied. Lecturers only.")
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


# Register view
def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        if password1 != password2:
            messages.error(request, "Passwords do not match")
        elif User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
        elif User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists")
        else:
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                password=password1,
                is_active=False  # Set to False so users need admin approval
            )
            messages.success(request, "Account created successfully! Please login.")
            return redirect('login')

    return render(request, 'analytics/auth/register.html')


def login_view(request):
    # Redirect if already logged in
    if request.user.is_authenticated:
        if request.user.is_staff and request.user.is_active:
            return redirect('dashboard')
        elif request.user.is_active:
            return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        role = request.POST.get('role')  # 'administrator' or 'lecturer'
        
        user = authenticate(request, username=username, password=password)
        
        if user:
            if not user.is_active:
                messages.error(request, "Your account is pending admin approval.")
                return render(request, 'analytics/auth/login.html')
            
            # Role-based validation
            if role == 'administrator':
                # Admin must be staff AND active
                if user.is_staff and user.is_active:
                    login(request, user)
                    return redirect('dashboard')
                else:
                    messages.error(request, "You don't have administrator privileges.")
            
            elif role == 'lecturer':
                # Lecturer must be active AND NOT staff
                if user.is_active and not user.is_staff:
                    login(request, user)
                    return redirect('home')
                else:
                    messages.error(request, "You don't have lecturer privileges.")
            
            else:
                messages.error(request, "Invalid role selected.")
        else:
            messages.error(request, "Invalid username or password")
    
    return render(request, 'analytics/auth/login.html')


# Logout view
@login_required(login_url='login')
def logout_view(request):
    user_name = request.user.get_full_name() or request.user.username
    logout(request)
    messages.success(request, f"Goodbye {user_name}! You have been logged out successfully.")
    return redirect('login')


# Protected dashboard for administrators
@admin_required
def dashboard(request):
    # You can add admin-specific data here
    context = {
        'total_lecturers': User.objects.filter(is_staff=False, is_active=True).count(),
        'pending_approvals': User.objects.filter(is_active=False).count(),
    }
    
    return render(request, 'analytics/admin/dashboard.html', context)


# Admin - Lecturers page
@admin_required
def lecturers(request):
    return render(request, 'analytics/admin/lecturers.html')


# Home page for lecturers
@lecturer_required
def home(request):
    return render(request, 'analytics/lecturer/home.html')


@lecturer_required
def teaching_records(request):
    return render(request, 'analytics/lecturer/teaching_records.html')


@lecturer_required
def workload(request):
    return render(request, 'analytics/lecturer/workload.html')