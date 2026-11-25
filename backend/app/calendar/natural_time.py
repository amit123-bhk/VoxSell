"""
Natural Language Date & Time Parser with Asia/Kolkata (IST) Timezone Support.

Parses colloquial English, Hindi, and Hinglish scheduling expressions into standardized
timezone-aware UTC and IST datetime objects.
"""

import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Optional, Tuple

DEFAULT_TIMEZONE = ZoneInfo("Asia/Kolkata")


class NaturalTimeParser:
    """
    Parses conversational relative times like 'kal shaam 5 baje', 'tomorrow 3pm',
    'next Tuesday morning' into datetime objects.
    """

    WEEKDAYS = {
        "monday": 0, "somwar": 0,
        "tuesday": 1, "mangalwar": 1,
        "wednesday": 2, "budhwar": 2,
        "thursday": 3, "guruwar": 3, "veervar": 3,
        "friday": 4, "shukrawar": 4,
        "saturday": 5, "shaniwar": 5,
        "sunday": 6, "ravivar": 6, "aitwar": 6,
    }

    @classmethod
    def parse(cls, phrase: str, base_time: Optional[datetime] = None) -> Optional[datetime]:
        """
        Parses time string into a timezone-aware datetime in Asia/Kolkata.
        """
        now = base_time or datetime.now(DEFAULT_TIMEZONE)
        cleaned = phrase.lower().strip()

        target_date = now.date()

        # 1. Day resolution (today, tomorrow, day after tomorrow, Hindi equivalents)
        if any(w in cleaned for w in ["parson", "day after tomorrow"]):
            target_date = now.date() + timedelta(days=2)
        elif any(w in cleaned for w in ["kal", "tomorrow", "agli subah"]):
            target_date = now.date() + timedelta(days=1)
        elif any(w in cleaned for w in ["aaj", "today", "this afternoon", "tonight"]):
            target_date = now.date()
        else:
            # Check for weekday (e.g. 'next tuesday', 'wednesday')
            for day_name, day_num in cls.WEEKDAYS.items():
                if day_name in cleaned:
                    days_ahead = day_num - now.weekday()
                    if days_ahead <= 0:  # Target day already happened this week
                        days_ahead += 7
                    target_date = now.date() + timedelta(days=days_ahead)
                    break

        # 2. Hour and Minute resolution
        target_hour = 17  # Default 5 PM
        target_minute = 0

        # Extract number before 'pm', 'am', 'baje', or bare hour
        time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm|baje|o\'clock)?', cleaned)
        if time_match:
            hr = int(time_match.group(1))
            mn = int(time_match.group(2)) if time_match.group(2) else 0
            meridiem = time_match.group(3)

            is_evening = any(w in cleaned for w in ["shaam", "evening", "dopahar", "afternoon", "raat", "night", "pm"])
            is_morning = any(w in cleaned for w in ["subah", "morning", "am"])

            if meridiem == "pm" or (is_evening and hr < 12):
                if hr < 12:
                    hr += 12
            elif meridiem == "am" or is_morning:
                if hr == 12:
                    hr = 0
            elif meridiem == "baje" and is_evening and hr < 12:
                hr += 12

            target_hour = hr
            target_minute = mn
        else:
            # Relative periods
            if any(w in cleaned for w in ["morning", "subah"]):
                target_hour = 11
            elif any(w in cleaned for w in ["afternoon", "dopahar"]):
                target_hour = 15
            elif any(w in cleaned for w in ["evening", "shaam"]):
                target_hour = 17

        try:
            target_dt = datetime(
                year=target_date.year,
                month=target_date.month,
                day=target_date.day,
                hour=target_hour,
                minute=target_minute,
                tzinfo=DEFAULT_TIMEZONE,
            )
            return target_dt
        except Exception:
            return None

    @classmethod
    def format_confirmation(cls, dt: datetime) -> str:
        """
        Formats datetime into a human-friendly confirmation string.
        e.g. 'Wednesday, Nov 26 at 5:00 PM IST'
        """
        local_dt = dt.astimezone(DEFAULT_TIMEZONE)
        return local_dt.strftime("%A, %b %d at %I:%M %p IST")
