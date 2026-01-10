from analytics.models import LecturerSettings, Lecturer

def user_settings(request):
    """Add user settings to all template contexts automatically"""
    if request.user.is_authenticated and not request.user.is_staff:
        try:
            lecturer = Lecturer.objects.get(user=request.user)
            settings, _ = LecturerSettings.objects.get_or_create(lecturer=lecturer)
            return {'settings': settings}
        except Lecturer.DoesNotExist:
            pass
    
    # Default settings for non-lecturers
    return {
        'settings': {
            'theme': 'light',
            'date_format': 'YYYY-MM-DD'
        }
    }