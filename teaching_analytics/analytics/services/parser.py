import pandas as pd
from datetime import datetime, time
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


def parse_time(x):
    """Parse time from various formats (HH:MM AM/PM or HH:MM 24-hour)"""
    if pd.isna(x):
        return None
    
    x_str = str(x).strip()
    
    # Handle empty strings
    if not x_str or x_str == 'nan':
        return None
    
    # Try parsing HH:MM format (24-hour)
    if ':' in x_str:
        try:
            # Remove any AM/PM and extra spaces
            x_str = x_str.replace('AM', '').replace('PM', '').strip()
            parts = x_str.split(':')
            if len(parts) == 2:
                hour = int(parts[0])
                minute = int(parts[1])
                return time(hour, minute)
        except:
            pass
    
    # Handle Excel serial time (fraction of day)
    try:
        if isinstance(x, float) and 0 <= x < 1:
            seconds = int(x * 86400)
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return time(hours, minutes)
    except:
        pass
    
    return None


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

    print(f"Total rows read: {len(df)}")
    print(f"Available columns: {df.shape[1]}")

    # CORRECT Column mapping based on actual file structure:
    # Column 1 = Date (Excel serial)
    # Column 2 = Time In (Excel decimal)
    # Column 3 = Time Out (Excel decimal)
    # Column 6 = Lecture Type (e.g., "Introduction", "Topology")
    # Column 16 = Session Duration in minutes (e.g., 180)
    
    if df.shape[1] < 17:
        raise ValueError(f"Not enough columns in file. Expected at least 17, found {df.shape[1]}")
    
    df = df[[1, 2, 3, 6, 16]]
    df.columns = ["date_raw", "time_in_raw", "time_out_raw", "lecture_type_raw", "minutes_raw"]

    print(f"\nProcessing data...")

    # Convert Excel serial date
    df["date"] = pd.to_datetime(
        df["date_raw"],
        unit="D",
        origin="1899-12-30",
        errors="coerce"
    ).dt.date
    
    # Parse time_in and time_out (these are Excel decimal times)
    df["time_in"] = df["time_in_raw"].apply(parse_time)
    df["time_out"] = df["time_out_raw"].apply(parse_time)
    
    # Get minutes directly from column 16
    df["minutes"] = pd.to_numeric(df["minutes_raw"], errors='coerce').fillna(0).astype(int)
    
    # Parse lecture type
    df["lecture_type"] = df["lecture_type_raw"].apply(
        lambda x: str(x).strip() if pd.notna(x) and str(x).strip() != 'nan' else None
    )
    
    # Show filtering steps
    print(f"\nBefore filtering: {len(df)} rows")
    print(f"Rows with valid dates: {df['date'].notna().sum()}")
    print(f"Rows with minutes > 0: {(df['minutes'] > 0).sum()}")
    
    # Filter valid rows
    df = df.dropna(subset=["date"])
    print(f"After dropping NaN dates: {len(df)} rows")
    
    df = df[df["minutes"] > 0]
    print(f"After filtering minutes > 0: {len(df)} rows")

    print(f"\nFound {len(df)} valid teaching sessions in file")
    
    # Show first few sessions for verification
    if len(df) > 0:
        print("\nFirst 3 sessions:")
        for idx, row in df.head(3).iterrows():
            print(f"  {row['date']} | {row['lecture_type']} | {row['time_in']}-{row['time_out']} | {row['minutes']} mins")

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
                        "time_in": row.time_in,
                        "time_out": row.time_out,
                        "lecture_type": row.lecture_type,
                        "week_number": week_number,
                        "month": month,
                    }
                )
                
                if was_created:
                    created += 1
                    print(f"  Created: {row.date} | {row.lecture_type} | {row.time_in} - {row.time_out} | {row.minutes} mins")
                else:
                    # Update existing session if data changed
                    changed = False
                    if obj.minutes != row.minutes:
                        obj.minutes = row.minutes
                        changed = True
                    if obj.time_in != row.time_in:
                        obj.time_in = row.time_in
                        changed = True
                    if obj.time_out != row.time_out:
                        obj.time_out = row.time_out
                        changed = True
                    if obj.lecture_type != row.lecture_type:
                        obj.lecture_type = row.lecture_type
                        changed = True
                    
                    if changed:
                        obj.week_number = week_number
                        obj.month = month
                        obj.save()
                        updated += 1
                        print(f"  Updated: {row.date} | {row.lecture_type} | {row.time_in} - {row.time_out} | {row.minutes} mins")
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