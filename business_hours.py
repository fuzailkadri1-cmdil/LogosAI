from datetime import datetime
import json
import re

def parse_time(time_str):
    """Parse time string like '9am', '9:00 AM', '21:00' to hour (0-23)"""
    time_str = time_str.strip().lower()
    
    patterns = [
        (r'(\d{1,2}):(\d{2})\s*(am|pm)', lambda m: int(m.group(1)) + (12 if m.group(3) == 'pm' and int(m.group(1)) != 12 else 0) - (12 if m.group(3) == 'am' and int(m.group(1)) == 12 else 0)),
        (r'(\d{1,2})\s*(am|pm)', lambda m: int(m.group(1)) + (12 if m.group(2) == 'pm' and int(m.group(1)) != 12 else 0) - (12 if m.group(2) == 'am' and int(m.group(1)) == 12 else 0)),
        (r'(\d{1,2}):(\d{2})', lambda m: int(m.group(1))),
    ]
    
    for pattern, extractor in patterns:
        match = re.match(pattern, time_str)
        if match:
            return extractor(match)
    
    return None


def parse_hours_range(hours_str):
    """Parse hours string like '9am-5pm' or '9:00 AM - 5:00 PM' to (open_hour, close_hour)"""
    hours_str = hours_str.strip().lower()
    
    if 'closed' in hours_str:
        return None
    
    parts = re.split(r'\s*[-–to]+\s*', hours_str)
    if len(parts) == 2:
        open_hour = parse_time(parts[0])
        close_hour = parse_time(parts[1])
        if open_hour is not None and close_hour is not None:
            return (open_hour, close_hour)
    
    return None


def get_day_key(day_of_week):
    """Get the day key (0=Monday, 6=Sunday) to day name mappings"""
    day_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    return day_names[day_of_week]


def is_store_open(business_hours_config, current_time=None):
    """
    Check if store is currently open based on business hours configuration.
    
    Args:
        business_hours_config: dict or JSON string with business hours
            Example: {"monday-friday": "9am-5pm", "saturday": "10am-4pm", "sunday": "closed"}
        current_time: datetime object (defaults to now in UTC)
    
    Returns:
        dict with 'is_open' (bool), 'hours_today' (str), 'next_open' (str)
    """
    if current_time is None:
        current_time = datetime.utcnow()
    
    if isinstance(business_hours_config, str):
        try:
            business_hours_config = json.loads(business_hours_config)
        except:
            business_hours_config = {}
    
    if not business_hours_config:
        # No hours configured — default to standard 9-5 Mon-Fri
        day_of_week = current_time.weekday()
        current_hour = current_time.hour
        if day_of_week < 5 and 9 <= current_hour < 17:
            return {'is_open': True, 'hours_today': '9am-5pm', 'next_open': None}
        return {'is_open': False, 'hours_today': 'Closed', 'next_open': 'next business day'}
    
    day_of_week = current_time.weekday()
    current_hour = current_time.hour
    day_name = get_day_key(day_of_week)
    
    hours_today = None
    
    for key, hours in business_hours_config.items():
        key_lower = key.lower()
        
        if day_name in key_lower:
            hours_today = hours
            break
        
        if 'monday-friday' in key_lower or 'mon-fri' in key_lower:
            if day_of_week < 5:
                hours_today = hours
                break
        
        if 'saturday-sunday' in key_lower or 'sat-sun' in key_lower or 'weekend' in key_lower:
            if day_of_week >= 5:
                hours_today = hours
                break
    
    if hours_today is None:
        return {'is_open': False, 'hours_today': 'Closed', 'next_open': 'tomorrow'}
    
    if 'closed' in hours_today.lower():
        return {'is_open': False, 'hours_today': 'Closed', 'next_open': 'tomorrow'}
    
    hours_range = parse_hours_range(hours_today)
    if hours_range is None:
        return {'is_open': True, 'hours_today': hours_today, 'next_open': None}
    
    open_hour, close_hour = hours_range
    is_open = open_hour <= current_hour < close_hour
    
    if is_open:
        return {'is_open': True, 'hours_today': hours_today, 'next_open': None}
    else:
        if current_hour < open_hour:
            next_open = f"at {open_hour}:00"
        else:
            next_open = "tomorrow"
        return {'is_open': False, 'hours_today': hours_today, 'next_open': next_open}


def format_business_hours_for_speech(business_hours_config):
    """Format business hours for natural speech output"""
    if isinstance(business_hours_config, str):
        try:
            business_hours_config = json.loads(business_hours_config)
        except:
            return "Monday through Friday, 9 AM to 5 PM"
    
    if not business_hours_config:
        return "Monday through Friday, 9 AM to 5 PM"
    
    parts = []
    for key, hours in business_hours_config.items():
        parts.append(f"{key}: {hours}")
    
    return ", ".join(parts)
