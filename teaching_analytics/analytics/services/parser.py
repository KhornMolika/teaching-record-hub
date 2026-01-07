import pandas as pd
from datetime import date
from django.db import transaction
from analytics.models import TeachingSession

def to_minutes(x):
    """Convert H:MM to total minutes"""
    x = str(x).strip()
    if ":" in x:
        h, m = x.split(":")
        return int(h) * 60 + int(m)
    return 0


def parse_xlsb_and_create_sessions(teaching_file):
    """
    Reads XLSB file and creates TeachingSession rows.
    One row = one teaching day.
    """

    file_path = teaching_file.file_name.path
    lecturer = teaching_file.lecturer
    subject = teaching_file.subject

    # READ XLSB (adjust based on your real format)
    df = pd.read_excel(
        file_path,
        engine="pyxlsb",
        sheet_name="1",
        skiprows=29,
        header=None
    )

    # Column mapping (your confirmed format)
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

    with transaction.atomic():
        for row in df.itertuples():
            week_number = row.date.isocalendar()[1]
            month = row.date.month

            obj, was_created = TeachingSession.objects.get_or_create(
                lecturer=lecturer,
                subject=subject, # assign later or auto-detect
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
