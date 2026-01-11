from django.shortcuts import render
from django.contrib.auth.models import User

from analytics.services.decorators import admin_required


@admin_required
def dashboard(request):
    """Admin dashboard with system statistics"""
    context = {
        'total_lecturers': User.objects.filter(is_staff=False, is_active=True).count(),
        'pending_approvals': User.objects.filter(is_active=False).count(),
    }
    
    return render(request, 'analytics/admin/dashboard.html', context)


@admin_required
def lecturers(request):
    """Admin lecturers management page"""
    return render(request, 'analytics/admin/lecturers.html')