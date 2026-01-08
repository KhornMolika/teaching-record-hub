# from django.db.models import Sum
# from analytics.models import TeachingSession, TeachingSummary

# def generate_summary(lecturer, subject, start_date, end_date):
#     qs = TeachingSession.objects.filter(
#         lecturer=lecturer,
#         subject=subject,
#         date__range=(start_date, end_date)
#     )

#     total_minutes = qs.aggregate(
#         total=Sum("minutes")
#     )["total"] or 0

#     weeks = qs.values("week_number").distinct().count()
#     avg_minutes = total_minutes // weeks if weeks else 0

#     summary = TeachingSummary.objects.create(
#         lecturer=lecturer,
#         subject=subject,
#         start_date=start_date,
#         end_date=end_date,
#         total_minutes=total_minutes,
#         average_minutes_per_week=avg_minutes,
#         completion_percentage=0,  # Phase 1 placeholder
#     )

#     return summary


from django.db.models import Sum, Avg, Count
from analytics.models import TeachingSession, TeachingSummary
from datetime import timedelta


def generate_summary(lecturer, subject, start_date, end_date):
    """
    Generate summary for a single lecturer-subject combination.
    Returns the created TeachingSummary object.
    """
    sessions = TeachingSession.objects.filter(
        lecturer=lecturer,
        subject=subject,
        date__range=[start_date, end_date]
    )

    if not sessions.exists():
        return None

    # Calculate totals
    total_minutes = sessions.aggregate(Sum('minutes'))['minutes__sum'] or 0
    
    # Calculate weeks
    weeks = sessions.values('week_number').distinct().count()
    average_minutes_per_week = total_minutes // weeks if weeks > 0 else 0
    
    # Calculate completion percentage (example: based on expected 15 weeks)
    expected_weeks = 15
    completion_percentage = (weeks / expected_weeks) * 100 if expected_weeks > 0 else 0
    
    # Create or update summary
    summary, created = TeachingSummary.objects.update_or_create(
        lecturer=lecturer,
        subject=subject,
        start_date=start_date,
        end_date=end_date,
        defaults={
            'total_minutes': total_minutes,
            'average_minutes_per_week': average_minutes_per_week,
            'completion_percentage': min(completion_percentage, 100.0),
        }
    )
    
    return summary


def generate_multi_subject_summaries(lecturer, subjects, start_date, end_date):
    """
    Generate summaries for multiple subjects and create a consolidated summary.
    
    Args:
        lecturer: Lecturer object
        subjects: List of Subject objects
        start_date: Start date for the period
        end_date: End date for the period
    
    Returns:
        dict with 'individual_summaries' (list) and 'consolidated_summary' (TeachingSummary)
    """
    individual_summaries = []
    
    # Generate individual summaries for each subject
    for subject in subjects:
        summary = generate_summary(lecturer, subject, start_date, end_date)
        if summary:
            individual_summaries.append(summary)
    
    # Generate consolidated summary (all subjects combined)
    consolidated_summary = None
    if individual_summaries:
        # Get all sessions for all subjects
        all_sessions = TeachingSession.objects.filter(
            lecturer=lecturer,
            subject__in=subjects,
            date__range=[start_date, end_date]
        )
        
        if all_sessions.exists():
            # Calculate combined totals
            total_minutes = all_sessions.aggregate(Sum('minutes'))['minutes__sum'] or 0
            
            # Calculate unique weeks across all subjects
            unique_weeks = all_sessions.values('week_number').distinct().count()
            average_minutes_per_week = total_minutes // unique_weeks if unique_weeks > 0 else 0
            
            # Expected weeks
            expected_weeks = 15
            completion_percentage = (unique_weeks / expected_weeks) * 100 if expected_weeks > 0 else 0
            
            # Create a "consolidated" subject entry if needed
            from analytics.models import Subject
            consolidated_subject_code = f"CONSOLIDATED_{lecturer.lecturer_id}"
            consolidated_subject, _ = Subject.objects.get_or_create(
                subject_code=consolidated_subject_code,
                defaults={
                    'subject_name': f'All Subjects - {lecturer.user.get_full_name()}',
                    'degree_level': 'Multiple',
                    'major': 'Combined'
                }
            )
            
            # Create consolidated summary
            consolidated_summary, _ = TeachingSummary.objects.update_or_create(
                lecturer=lecturer,
                subject=consolidated_subject,
                start_date=start_date,
                end_date=end_date,
                defaults={
                    'total_minutes': total_minutes,
                    'average_minutes_per_week': average_minutes_per_week,
                    'completion_percentage': min(completion_percentage, 100.0),
                }
            )
    
    return {
        'individual_summaries': individual_summaries,
        'consolidated_summary': consolidated_summary
    }


def format_summary_report(individual_summaries, consolidated_summary):
    """
    Format a text report of summaries for display.
    
    Returns:
        str: Formatted report
    """
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("TEACHING SUMMARY REPORT")
    report_lines.append("=" * 80)
    
    if individual_summaries:
        report_lines.append("\nINDIVIDUAL SUBJECT SUMMARIES:")
        report_lines.append("-" * 80)
        
        for i, summary in enumerate(individual_summaries, 1):
            report_lines.append(f"\n{i}. {summary.subject.subject_code} - {summary.subject.subject_name}")
            report_lines.append(f"   Period: {summary.start_date} to {summary.end_date}")
            report_lines.append(f"   Total Minutes: {summary.total_minutes} ({summary.total_minutes // 60}h {summary.total_minutes % 60}m)")
            report_lines.append(f"   Average per Week: {summary.average_minutes_per_week} minutes")
            report_lines.append(f"   Completion: {summary.completion_percentage:.1f}%")
    
    if consolidated_summary:
        report_lines.append("\n" + "=" * 80)
        report_lines.append("CONSOLIDATED SUMMARY (ALL SUBJECTS)")
        report_lines.append("=" * 80)
        report_lines.append(f"Lecturer: {consolidated_summary.lecturer}")
        report_lines.append(f"Period: {consolidated_summary.start_date} to {consolidated_summary.end_date}")
        report_lines.append(f"Total Minutes: {consolidated_summary.total_minutes} ({consolidated_summary.total_minutes // 60}h {consolidated_summary.total_minutes % 60}m)")
        report_lines.append(f"Average per Week: {consolidated_summary.average_minutes_per_week} minutes")
        report_lines.append(f"Completion: {consolidated_summary.completion_percentage:.1f}%")
        report_lines.append(f"Number of Subjects: {len(individual_summaries)}")
    
    report_lines.append("=" * 80)
    
    return "\n".join(report_lines)