from analytics.models import LecturerSettings, Lecturer, AdminSettings

def user_settings(request):
    """Add user-specific and system-wide settings to all template contexts."""
    context = {
        'settings': {
            'theme': 'light',
            'date_format': 'YYYY-MM-DD'
        },
        'admin_settings': None
    }

    if request.user.is_authenticated:
        if request.user.is_staff:
            try:
                # For admins, get their specific admin settings
                admin_settings, _ = AdminSettings.objects.get_or_create(user=request.user)
                context['admin_settings'] = admin_settings
                # Admins can also have personal view settings, treat them like a lecturer for this
                lecturer, _ = Lecturer.objects.get_or_create(user=request.user)
                settings, _ = LecturerSettings.objects.get_or_create(lecturer=lecturer)
                context['settings'] = settings
            except Exception:
                pass # Avoid errors if something goes wrong
        else:
            try:
                # For lecturers, get their personal settings
                lecturer = Lecturer.objects.get(user=request.user)
                settings, _ = LecturerSettings.objects.get_or_create(lecturer=lecturer)
                context['settings'] = settings
            except Lecturer.DoesNotExist:
                pass # Use default context
    
    return context