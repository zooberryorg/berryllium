# settings and utilities for date and time formats

DATE_FORMATS = {
    "dmy": {"label": "DD/MM/YYYY (31/12/2026)", "format": "d/m/Y", "placeholder": "DD/MM/YYYY", "week_start": 1},
    "mdy": {"label": "MM/DD/YYYY (12/31/2026)", "format": "m/d/Y", "placeholder": "MM/DD/YYYY", "week_start": 0},
    "ymd": {"label": "YYYY-MM-DD (2026-12-31)", "format": "Y-m-d", "placeholder": "YYYY-MM-DD", "week_start": 1},
}

TIME_FORMATS = {
    "24h": {"label": "24-hour (14:30)", "django": "H:i", "picker": "H:i", "placeholder": "HH:MM", "time_24hr": True},
    "12h": {"label": "12-hour (2:30 PM)", "django": "g:i A", "picker": "h:i K", "placeholder": "hh:mm AM", "time_24hr": False},
}

DEFAULT_DATE_FORMAT = "dmy"
DEFAULT_TIME_FORMAT = "24h"

DATE_FORMAT_CHOICES = [(key, value["label"]) for key, value in DATE_FORMATS.items()]
TIME_FORMAT_CHOICES = [(key, value["label"]) for key, value in TIME_FORMATS.items()]


def date_preferences(user=None):
    """Format strings for a user (or the defaults for anonymous visitors / user=None)."""
    date_key = getattr(user, "date_format", None) if getattr(user, "is_authenticated", False) else None
    time_key = getattr(user, "time_format", None) if getattr(user, "is_authenticated", False) else None
    date_format = DATE_FORMATS.get(date_key) or DATE_FORMATS[DEFAULT_DATE_FORMAT]
    time_format = TIME_FORMATS.get(time_key) or TIME_FORMATS[DEFAULT_TIME_FORMAT]

    return {
        # for Django's |date filter
        "date": date_format["format"],
        "time": time_format["django"],
        "datetime": f'{date_format["format"]}, {time_format["django"]}',
        # for the flatpickr date pickers
        "picker_date": date_format["format"],
        "picker_datetime": f'{date_format["format"]} {time_format["picker"]}',
        "time_24hr": time_format["time_24hr"],
        "week_start": date_format["week_start"],
        # input hints
        "date_placeholder": date_format["placeholder"],
        "datetime_placeholder": f'{date_format["placeholder"]} {time_format["placeholder"]}',
    }
