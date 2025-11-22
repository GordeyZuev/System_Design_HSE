from datetime import datetime, timezone
import math

def now():
    return datetime.now(timezone.utc)

def minutes_between(a: datetime, b: datetime) -> int:
    diff = b - a
    minutes = diff.total_seconds() / 60.0
    return int(math.ceil(minutes))
