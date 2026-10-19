from django import template
from django.utils.safestring import mark_safe
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

# --------------------------- template tags


@register.simple_tag
def gen_field(field, **kwargs):
    extra = {k.replace("_", "-"): v for k, v in kwargs.items()}
    return mark_safe(field.as_widget(attrs=extra))
