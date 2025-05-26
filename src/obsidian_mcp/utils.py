import re
from datetime import datetime, timedelta
from dateutil import parser as date_parser


def format_timestamp(timestamp_ms: int) -> str:
    dt = datetime.fromtimestamp(timestamp_ms / 1000)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def parse_date_filter(date_str: str) -> datetime:
    if "ago" in date_str.lower():
        if "week" in date_str.lower():
            weeks = int(re.search(r'(\d+)', date_str).group(1))
            return datetime.now() - timedelta(weeks=weeks)
        elif "day" in date_str.lower():
            days = int(re.search(r'(\d+)', date_str).group(1))
            return datetime.now() - timedelta(days=days)
    elif date_str.lower() == "today":
        return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        return date_parser.parse(date_str)