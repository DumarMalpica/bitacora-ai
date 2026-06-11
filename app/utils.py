from datetime import datetime
from zoneinfo import ZoneInfo


def now_in_timezone(timezone_name: str) -> datetime:
    return datetime.now(ZoneInfo(timezone_name))


def iso_week_key(value: datetime) -> str:
    year, week, _ = value.isocalendar()
    return f"{year}-W{week:02d}"


def previous_iso_week_key(value: datetime) -> str:
    year, week, weekday = value.isocalendar()
    days_since_monday = weekday - 1
    monday = value.date().toordinal() - days_since_monday
    previous_week_date = datetime.fromordinal(monday - 1).replace(tzinfo=value.tzinfo)
    return iso_week_key(previous_week_date)
