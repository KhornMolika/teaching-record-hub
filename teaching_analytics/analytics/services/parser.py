import pandas as pd
from datetime import date
from django.db import transaction
from analytics.models import TeachingSession, Subject
import re


def to_minutes(x):
    """Convert H:MM to total minutes"""
    x = str(x).strip()
    if ":" in x:
        h, m = x.split(":")
        return int(h) * 60 + int(m)
    return 0


def extract_subject_and_semester(file_path):
    """
    Extract subject information and semester from XLSB file header.
    Returns dict with subject_code, subject_name, degree_level, major, and semester.
    """
    # Read header rows
    df_header = pd.read_excel(
        file_path,
        engine="pyxlsb",
        sheet_name="1",
        nrows=15,
        header=None
    )
    
    # Initialize variables
    timeline = None
    subject_code = None
    subject_name = None
    degree_level = None
    major = None
    semester = "Unknown"
    
    # Extract data from specific rows (based on your file structure)
    for idx, row in df_header.iterrows():
        row_label = str(row[0]).strip() if pd.notna(row[0]) else ""
        
        # Timeline at row 2, column 3
        if 'Timeline' in row_label:
            timeline = str(row[3]).strip() if pd.notna(row[3]) else None
            print(f"Found Timeline at row {idx}: {timeline}")
        
        # Subject ID at row 8, column 3
        elif 'Subject ID' in row_label:
            subject_code = str(row[3]).strip() if pd.notna(row[3]) else None
            print(f"Found Subject ID at row {idx}: {subject_code}")
        
        # Subject Name at row 9, column 3
        elif 'Subject Name' in row_label:
            subject_name = str(row[3]).strip() if pd.notna(row[3]) else None
            print(f"Found Subject Name at row {idx}: {subject_name}")
        
        # Degree/Level at row 6, column 3
        elif 'Degree/Level' in row_label:
            degree_level = str(row[3]).strip() if pd.notna(row[3]) else None
            print(f"Found Degree/Level at row {idx}: {degree_level}")
        
        # Major at row 7, column 3
        elif 'Major' in row_label:
            major = str(row[3]).strip() if pd.notna(row[3]) else None
            print(f"Found Major at row {idx}: {major}")
    
    # Extract semester from timeline
    if timeline and timeline != 'nan':
        # Pattern: B8Y3S1 means Bachelor Year 3 Semester 1
        semester_match = re.search(r'B\d+Y(\d+)S(\d+)', timeline)
        if semester_match:
            year = semester_match.group(1)
            sem = semester_match.group(2)
            semester = f"Year {year} Semester {sem}"
        else:
            # Try to extract just the semester code
            code_match = re.search(r'(B\d+Y\d+S\d+)', timeline)
            if code_match:
                semester = code_match.group(1)
            else:
                # Use the first part before comma
                semester = timeline.split(',')[0].strip() if ',' in timeline else timeline
    
    # Validate extracted data
    if not subject_code or subject_code == 'nan':
        raise ValueError("Could not extract Subject ID from file. Please check file format.")
    if not subject_name or subject_name == 'nan':
        raise ValueError("Could not extract Subject Name from file. Please check file format.")
    
    # Set defaults for optional fields
    if not degree_level or degree_level == 'nan':
        degree_level = "Bachelor Degree"
    if not major or major == 'nan':
        major = "General"
    
    return {
        'subject_code': subject_code,
        'subject_name': subject_name,
        'degree_level': degree_level,
        'major': major,
        'semester': semester,
        'timeline': timeline if timeline else "Not found"
    }


def parse_xlsb_and_create_sessions(teaching_file):
    """
    Reads XLSB file, extracts subject info and semester, and creates TeachingSession rows.
    One row = one teaching day.
    """
    file_path = teaching_file.file_name.path
    lecturer = teaching_file.lecturer

    print("\n" + "="*80)
    print(f"PARSING FILE: {teaching_file.file_name.name}")
    print("="*80)

    # STEP 1: Extract subject information and semester from file
    try:
        info = extract_subject_and_semester(file_path)
        
        print(f"\n✓ Extracted Subject Info:")
        print(f"  - Subject Code: {info['subject_code']}")
        print(f"  - Subject Name: {info['subject_name']}")
        print(f"  - Degree Level: {info['degree_level']}")
        print(f"  - Major: {info['major']}")
        print(f"  - Semester: {info['semester']}")
        print(f"  - Timeline: {info['timeline']}")
        
        # Get or create the Subject
        subject, created = Subject.objects.get_or_create(
            subject_code=info['subject_code'],
            defaults={
                'subject_name': info['subject_name'],
                'degree_level': info['degree_level'],
                'major': info['major']
            }
        )
        
        if created:
            print(f"\n✓ Created new subject: {subject}")
        else:
            print(f"\n✓ Using existing subject: {subject}")
        
        # Update teaching_file with the extracted semester
        teaching_file.semester = info['semester']
        teaching_file.save()
        
    except Exception as e:
        print(f"\n✗ Error extracting subject/semester info: {e}")
        import traceback
        traceback.print_exc()
        raise ValueError(f"Could not extract subject and semester from file: {e}")

    # STEP 2: Read teaching session data
    print(f"\nReading session data from file...")
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

    print(f"Found {len(df)} valid teaching sessions in file")

    created = 0
    updated = 0
    skipped = 0

    # STEP 3: Create teaching sessions
    with transaction.atomic():
        for row in df.itertuples():
            week_number = row.date.isocalendar()[1]
            month = row.date.month

            try:
                obj, was_created = TeachingSession.objects.get_or_create(
                    lecturer=lecturer,
                    subject=subject,
                    date=row.date,
                    defaults={
                        "teaching_file": teaching_file,
                        "minutes": row.minutes,
                        "week_number": week_number,
                        "month": month,
                    }
                )
                
                if was_created:
                    created += 1
                else:
                    # Update existing session if minutes changed
                    if obj.minutes != row.minutes:
                        obj.minutes = row.minutes
                        obj.week_number = week_number
                        obj.month = month
                        obj.save()
                        updated += 1
                    else:
                        skipped += 1
                        
            except Exception as e:
                print(f"Error creating session for {row.date}: {e}")
                raise

    print(f"\n" + "="*80)
    print(f"PARSING COMPLETE")
    print(f"="*80)
    print(f"✓ Created: {created} new sessions")
    if updated > 0:
        print(f"✓ Updated: {updated} existing sessions")
    if skipped > 0:
        print(f"→ Skipped: {skipped} unchanged sessions")
    print("="*80 + "\n")

    return created