"""
business_hours.py — Store Hours Checking Utility

Parses human-readable business hours (e.g. "9am-5pm") stored as JSON
in the database and determines whether the store is currently open.

Used by the AI voice agent to decide:
  - Whether to escalate purchase inquiries to staff (during hours)
  - Whether to capture a callback lead (after hours)
  - What to say when a caller asks "what are your hours?"
"""

from datetime import datetime
import json
import re


def parse_time(time_str):
    """
    Convert a time string to a 24-hour integer hour value.

    Handles common formats like "9am", "9:00 AM", "21:00", "9:30pm".
    Only the hour portion is returned — minutes are ignored.

    Args:
        time_str (str): A time string in any common format.

    Returns:
        int or None: Hour in 24-hour format (0–23), or None if unparseable.

    Examples:
        parse_time("9am")    → 9
        parse_time("5pm")    → 17
        parse_time("21:00")  → 21
        parse_time("9:30 AM") → 9
    """
    time_str = time_str.strip().lower()

    # Each tuple is (regex pattern, lambda to extract the hour as int)
    patterns = [
        # "9:00 am" / "9:30 PM"
        (r'(\d{1,2}):(\d{2})\s*(am|pm)',
         lambda m: int(m.group(1)) + (12 if m.group(3) == 'pm' and int(m.group(1)) != 12 else 0)
                   - (12 if m.group(3) == 'am' and int(m.group(1)) == 12 else 0)),
        # "9am" / "5pm"
        (r'(\d{1,2})\s*(am|pm)',
         lambda m: int(m.group(1)) + (12 if m.group(2) == 'pm' and int(m.group(1)) != 12 else 0)
                   - (12 if m.group(2) == 'am' and int(m.group(1)) == 12 else 0)),
        # "21:00" (24-hour, no am/pm)
        (r'(\d{1,2}):(\d{2})',
         lambda m: int(m.group(1))),
    ]

    for pattern, extractor in patterns:
        match = re.match(pattern, time_str)
        if match:
            return extractor(match)

    return None


def parse_hours_range(hours_str):
    """
    Parse a time range string into open/close hours.

    Accepts separators: "-", "–" (en-dash), or " to ".

    Args:
        hours_str (str): A range like "9am-5pm", "9:00 AM – 5:00 PM",
                         "9am to 5pm", or "closed".

    Returns:
        tuple or None: (open_hour, close_hour) as ints, or None if the
                       string represents a closed day or can't be parsed.

    Examples:
        parse_hours_range("9am-5pm")  → (9, 17)
        parse_hours_range("closed")   → None
        parse_hours_range("9am-9pm")  → (9, 21)
    """
    hours_str = hours_str.strip().lower()

    if 'closed' in hours_str:
        return None

    # Split on dash, en-dash, or "to"
    parts = re.split(r'\s*[-–to]+\s*', hours_str)
    if len(parts) == 2:
        open_hour = parse_time(parts[0])
        close_hour = parse_time(parts[1])
        if open_hour is not None and close_hour is not None:
            return (open_hour, close_hour)

    return None


def get_day_key(day_of_week):
    """
    Convert Python's weekday integer to a lowercase day name.

    Args:
        day_of_week (int): 0 = Monday, 6 = Sunday (Python datetime convention).

    Returns:
        str: Lowercase day name, e.g. "monday", "saturday".
    """
    day_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    return day_names[day_of_week]


def is_store_open(business_hours_config, current_time=None):
    """
    Determine whether the store is currently open.

    Supports flexible day-range keys:
      - "monday-friday" / "mon-fri"
      - "saturday-sunday" / "sat-sun" / "weekend"
      - Individual day names: "monday", "tuesday", etc.

    Args:
        business_hours_config (dict or str): Business hours as a dict or
            JSON string. Example:
            {"monday-friday": "9am-5pm", "saturday": "10am-4pm", "sunday": "closed"}
        current_time (datetime, optional): The time to check against. Defaults
            to datetime.utcnow() if not provided.

    Returns:
        dict with keys:
            is_open (bool):     True if the store is currently open.
            hours_today (str):  The hours string for today, e.g. "9am-5pm".
            next_open (str):    When the store next opens, e.g. "at 9:00" or
                                "tomorrow". None if the store is currently open.
    """
    if current_time is None:
        current_time = datetime.utcnow()

    # Accept JSON string or pre-parsed dict
    if isinstance(business_hours_config, str):
        try:
            business_hours_config = json.loads(business_hours_config)
        except Exception:
            business_hours_config = {}

    # Default behaviour when no hours are configured: standard 9-5 Mon-Fri
    if not business_hours_config:
        day_of_week = current_time.weekday()
        current_hour = current_time.hour
        if day_of_week < 5 and 9 <= current_hour < 17:
            return {'is_open': True, 'hours_today': '9am-5pm', 'next_open': None}
        return {'is_open': False, 'hours_today': 'Closed', 'next_open': 'next business day'}

    day_of_week = current_time.weekday()
    current_hour = current_time.hour
    day_name = get_day_key(day_of_week)

    # Walk through config keys looking for one that covers today
    hours_today = None
    for key, hours in business_hours_config.items():
        key_lower = key.lower()

        # Exact day match: "monday", "tuesday", etc.
        if day_name in key_lower:
            hours_today = hours
            break

        # Weekday range: "monday-friday" or "mon-fri"
        if 'monday-friday' in key_lower or 'mon-fri' in key_lower:
            if day_of_week < 5:
                hours_today = hours
                break

        # Weekend range: "saturday-sunday" / "sat-sun" / "weekend"
        if 'saturday-sunday' in key_lower or 'sat-sun' in key_lower or 'weekend' in key_lower:
            if day_of_week >= 5:
                hours_today = hours
                break

    # No matching key found → store is closed today
    if hours_today is None:
        return {'is_open': False, 'hours_today': 'Closed', 'next_open': 'tomorrow'}

    # Explicit "closed" value
    if 'closed' in hours_today.lower():
        return {'is_open': False, 'hours_today': 'Closed', 'next_open': 'tomorrow'}

    # Parse the time range and check current hour
    hours_range = parse_hours_range(hours_today)
    if hours_range is None:
        # Can't parse range — assume open to avoid blocking callers
        return {'is_open': True, 'hours_today': hours_today, 'next_open': None}

    open_hour, close_hour = hours_range
    is_open = open_hour <= current_hour < close_hour

    if is_open:
        return {'is_open': True, 'hours_today': hours_today, 'next_open': None}
    else:
        # Tell callers when they can call back
        next_open = f"at {open_hour}:00" if current_hour < open_hour else "tomorrow"
        return {'is_open': False, 'hours_today': hours_today, 'next_open': next_open}


def format_business_hours_for_speech(business_hours_config):
    """
    Format business hours into a natural spoken string.

    Args:
        business_hours_config (dict or str): Business hours config.

    Returns:
        str: A readable string like "monday-friday: 9am-9pm, saturday-sunday: 10am-6pm".
             Falls back to "Monday through Friday, 9 AM to 5 PM" if config is empty.
    """
    if isinstance(business_hours_config, str):
        try:
            business_hours_config = json.loads(business_hours_config)
        except Exception:
            return "Monday through Friday, 9 AM to 5 PM"

    if not business_hours_config:
        return "Monday through Friday, 9 AM to 5 PM"

    parts = []
    for key, hours in business_hours_config.items():
        parts.append(f"{key}: {hours}")

    return ", ".join(parts)
