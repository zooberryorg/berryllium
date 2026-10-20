from berryllium.shared.dates import date_preferences as _date_preferences


def date_preferences(request):
    """Adds `date_prefs` (the visitor's date/time formats) to every template."""
    return {"date_prefs": _date_preferences(getattr(request, "user", None))}