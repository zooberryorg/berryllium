from datetime import timedelta

from django import template
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.timesince import timesince
from berryllium.shared.markdown_render import render_markdown

register = template.Library()

# --------------------------- filters


@register.filter
def get_item(list_obj, index):
    try:
        return list_obj[index]
    except (IndexError, ValueError, TypeError):
        return None

@register.filter
def markdown(value):
    """Usage: {{ mod.description|markdown }}"""
    return mark_safe(render_markdown(value))

@register.filter
def timeago(value):
    """Usage: {{ mod.last_updated|timeago }} -> "3 days ago" (largest unit only)."""
    if not value:
        return ""
    if timezone.now() - value < timedelta(minutes=1):
        return "just now"
    return f"{timesince(value, depth=1)} ago"

@register.filter
def compact(value):
    """Usage: {{ mod.download_count|compact }} -> 950, 1.2k, 34k, 1.5M"""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return value
    for limit, suffix in ((1_000_000, "M"), (1_000, "k")):
        if abs(number) >= limit:
            short = number / limit
            text = f"{short:.1f}" if abs(short) < 10 else f"{short:.0f}"
            return f"{text.removesuffix('.0')}{suffix}"
    return str(number)

# --------------------------- template tags


@register.simple_tag
def gen_field(field, **kwargs):
    extra = {k.replace("_", "-"): v for k, v in kwargs.items()}
    return mark_safe(field.as_widget(attrs=extra))
