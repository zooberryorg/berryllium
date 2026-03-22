from django import template
from django.utils.safestring import mark_safe
from widget_tweaks.templatetags.widget_tweaks import render_field

register = template.Library()

# --------------------------- filters


@register.filter
def get_item(list_obj, index):
    try:
        return list_obj[index]
    except (IndexError, ValueError, TypeError):
        return None


# --------------------------- template tags


@register.simple_tag
def gen_field(field, **kwargs):
    extra = {k.replace("_", "-"): v for k, v in kwargs.items()}
    return mark_safe(field.as_widget(attrs=extra))
