from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required

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
                is_active=False  # User needs to be activated by admin
            )
            login(request, user)
            return redirect('analytics/dashboard.html')

    return render(request, 'analytics/register.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        role = request.POST.get('role')  # 'administrator' or 'lecturer'
        
        user = authenticate(request, username=username, password=password)
        
        if user:
            if not user.is_active:
                messages.error(request, "Your account is pending admin approval.")
                return render(request, 'analytics/login.html')
            
            # Role-based validation
            if role == 'administrator':
                # Admin must be staff and active
                if user.is_staff and user.is_active:
                    login(request, user)
                    return redirect('dashboard')  # Use URL name, not file path
                else:
                    messages.error(request, "You don't have administrator privileges.")
            
            elif role == 'lecturer':
                # Lecturer must be active
                if user.is_active:
                    login(request, user)
                    return redirect('home')  # Use URL name, not file path
                else:
                    messages.error(request, "You don't have lecturer privileges.")
            
            else:
                messages.error(request, "Invalid role selected.")
        else:
            messages.error(request, "Invalid username or password")
    
    return render(request, 'analytics/login.html')


# Logout view
def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('login')


# Protected dashboard for administrators
@login_required(login_url='login')
def dashboard(request):
    # Only staff members (admins) can access dashboard
    if not request.user.is_staff:
        messages.error(request, "Access denied. Admins only.")
        return redirect('home')
    
    return render(request, 'analytics/dashboard.html')  # Use render, not redirect


# Home page for lecturers
@login_required(login_url='login')
def home(request):
    # Any active user can access home
    return render(request, 'analytics/home.html')  # Use render, not redirect