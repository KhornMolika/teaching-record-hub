from datetime import datetime

def format_date(date, format_string):
    """Format a date according to the specified format string"""
    if not date:
        return ''
    
    if not isinstance(date, datetime):
        from datetime import date as date_type
        if isinstance(date, date_type):
            date = datetime.combine(date, datetime.min.time())
    
    format_map = {
        'YYYY-MM-DD': '%Y-%m-%d',
        'MM/DD/YYYY': '%m/%d/%Y',
        'DD/MM/YYYY': '%d/%m/%Y',
        'DD-MM-YYYY': '%d-%m-%Y',
        'MMMM DD, YYYY': '%B %d, %Y',
        'DD MMMM YYYY': '%d %B %Y',
        'MMM DD, YYYY': '%b %d, %Y',
        'DD MMM YYYY': '%d %b %Y'
    }
    
    python_format = format_map.get(format_string, '%Y-%m-%d')
    return date.strftime(python_format)


def get_python_date_format(format_string):
    """Convert custom format string to Python strftime format"""
    format_map = {
        'YYYY-MM-DD': '%Y-%m-%d',
        'MM/DD/YYYY': '%m/%d/%Y',
        'DD/MM/YYYY': '%d/%m/%Y',
        'DD-MM-YYYY': '%d-%m-%Y',
        'MMMM DD, YYYY': '%B %d, %Y',
        'DD MMMM YYYY': '%d %B %Y',
        'MMM DD, YYYY': '%b %d, %Y',
        'DD MMM YYYY': '%d %b %Y'
    }
    return format_map.get(format_string, '%Y-%m-%d')


def get_user_settings(request):
    """Get user settings - helper function"""
    from analytics.models import LecturerSettings, Lecturer
    
    if request.user.is_authenticated and not request.user.is_staff:
        try:
            lecturer = Lecturer.objects.get(user=request.user)
            settings, _ = LecturerSettings.objects.get_or_create(lecturer=lecturer)
            return settings
        except Lecturer.DoesNotExist:
            pass
    return None