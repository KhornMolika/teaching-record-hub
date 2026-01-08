import pandas as pd
from datetime import date
from django.db import transaction
from analytics.models import TeachingSession, Subject

def to_minutes(x):
    """Convert H:MM to total minutes"""
    x = str(x).strip()
    if ":" in x:
        h, m = x.split(":")
        return int(h) * 60 + int(m)
    return 0


def extract_subject_info(file_path):
    """
    Extract subject information from XLSB file header.
    Adjust row/column indices based on your actual file format.
    """
    # Read header rows (before skiprows=29)
    df_header = pd.read_excel(
        file_path,
        engine="pyxlsb",
        sheet_name="1",
        nrows=29,  # Read only header rows
        header=None
    )
    
    # Example: Extract subject code and name from specific cells
    # Adjust these indices based on your file structure
    subject_code = str(df_header.iloc[5, 1]).strip()  # Row 6, Column B
    subject_name = str(df_header.iloc[6, 1]).strip()  # Row 7, Column B
    
    # Optional: Extract degree level and major if available
    degree_level = str(df_header.iloc[7, 1]).strip() if len(df_header) > 7 else "Bachelor"
    major = str(df_header.iloc[8, 1]).strip() if len(df_header) > 8 else "General"
    
    return {
        'subject_code': subject_code,
        'subject_name': subject_name,
        'degree_level': degree_level,
        'major': major
    }


def parse_xlsb_and_create_sessions(teaching_file):
    """
    Reads XLSB file, extracts subject info, and creates TeachingSession rows.
    One row = one teaching day.
    """
    file_path = teaching_file.file_name.path
    lecturer = teaching_file.lecturer

    # STEP 1: Extract subject information from file
    try:
        subject_info = extract_subject_info(file_path)
        
        # Get or create the Subject
        subject, _ = Subject.objects.get_or_create(
            subject_code=subject_info['subject_code'],
            defaults={
                'subject_name': subject_info['subject_name'],
                'degree_level': subject_info['degree_level'],
                'major': subject_info['major']
            }
        )
        
        # Update teaching_file with the extracted subject
        teaching_file.subject = subject
        teaching_file.save()
        
    except Exception as e:
        print(f"Error extracting subject info: {e}")
        # Fallback to existing subject if extraction fails
        subject = teaching_file.subject
        if not subject:
            raise ValueError("Could not extract subject from file and no subject assigned to teaching_file")

    # STEP 2: Read teaching session data
    df = pd.read_excel(
        file_path,
        engine="pyxlsb",
        sheet_name="1",
        skiprows=29,
        header=None
    )

    # Column mapping
    df = df[[1, 5]]
    df.columns = ["date_raw", "time_raw"]

    # Convert Excel serial date
    df["date"] = pd.to_datetime(
        df["date_raw"],
        unit="D",
        origin="1899-12-30",
        errors="coerce"
    ).dt.date

    df["minutes"] = df["time_raw"].apply(to_minutes)
    df = df.dropna(subset=["date"])
    df = df[df["minutes"] > 0]

    created = 0

    # STEP 3: Create teaching sessions
    with transaction.atomic():
        for row in df.itertuples():
            week_number = row.date.isocalendar()[1]
            month = row.date.month

            obj, was_created = TeachingSession.objects.get_or_create(
                lecturer=lecturer,
                subject=subject,
                teaching_file=teaching_file,
                date=row.date,
                defaults={
                    "minutes": row.minutes,
                    "week_number": week_number,
                    "month": month,
                }
            )
            if was_created:
                created += 1

    return created