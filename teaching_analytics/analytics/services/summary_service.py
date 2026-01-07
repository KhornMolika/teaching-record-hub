from django.db.models import Sum
from analytics.models import TeachingSession, TeachingSummary

def generate_summary(lecturer, subject, start_date, end_date):
    qs = TeachingSession.objects.filter(
        lecturer=lecturer,
        subject=subject,
        date__range=(start_date, end_date)
    )

    total_minutes = qs.aggregate(
        total=Sum("minutes")
    )["total"] or 0

    weeks = qs.values("week_number").distinct().count()
    avg_minutes = total_minutes // weeks if weeks else 0

    summary = TeachingSummary.objects.create(
        lecturer=lecturer,
        subject=subject,
        start_date=start_date,
        end_date=end_date,
        total_minutes=total_minutes,
        average_minutes_per_week=avg_minutes,
        completion_percentage=0,  # Phase 1 placeholder
    )

    return summary
