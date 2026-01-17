from analytics.models import Lecturer, TeachingSession, WorkloadPrediction, AdminSettings, Subject
from django.db.models import Sum, Avg
import datetime

def update_workload_predictions():
    """
    Calculates and updates workload predictions for all approved lecturers.
    """
    # Clear old predictions
    WorkloadPrediction.objects.all().delete()

    # Get system-wide settings
    try:
        admin_settings = AdminSettings.objects.first()
        if not admin_settings:
            # If no admin settings, we can't proceed
            return
    except AdminSettings.DoesNotExist:
        return

    SEMESTER_WEEKS = 14  # Standard semester length
    TARGET_HOURS = admin_settings.default_workload_target
    OVERLOAD_THRESHOLD = admin_settings.risk_threshold_overload
    UNDERLOAD_THRESHOLD = admin_settings.risk_threshold_underload

    approved_lecturers = Lecturer.objects.filter(is_approved=True, user__is_staff=False)

    for lecturer in approved_lecturers:
        subjects = Subject.objects.filter(sessions__lecturer=lecturer).distinct()

        for subject in subjects:
            sessions = TeachingSession.objects.filter(lecturer=lecturer, subject=subject)
            if not sessions.exists():
                continue

            # Calculate current progress
            current_minutes_agg = sessions.aggregate(total_minutes=Sum('minutes'))
            current_minutes = current_minutes_agg['total_minutes'] or 0

            weeks_with_sessions = sessions.values('week_number').distinct().count()
            
            # Calculate average weekly minutes
            if weeks_with_sessions > 0:
                avg_weekly_minutes = current_minutes / weeks_with_sessions
            else:
                avg_weekly_minutes = 0

            # Predict total minutes for the semester
            remaining_weeks = max(0, SEMESTER_WEEKS - weeks_with_sessions)
            predicted_total_minutes = current_minutes + (avg_weekly_minutes * remaining_weeks)

            # Determine risk level
            target_minutes = TARGET_HOURS * 60
            risk_level = "Normal"
            if target_minutes > 0:
                overload_limit = target_minutes * (OVERLOAD_THRESHOLD / 100)
                underload_limit = target_minutes * (UNDERLOAD_THRESHOLD / 100)
                
                if predicted_total_minutes > overload_limit:
                    risk_level = "Overload"
                elif predicted_total_minutes < underload_limit:
                    risk_level = "Underload"

            # Create new prediction
            WorkloadPrediction.objects.create(
                lecturer=lecturer,
                subject=subject,
                current_minutes=current_minutes,
                predicted_total_minutes=predicted_total_minutes,
                remaining_weeks=remaining_weeks,
                risk_level=risk_level
            )
