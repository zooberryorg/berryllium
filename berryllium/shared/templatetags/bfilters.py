from django import template
from django.utils.safestring import mark_safe

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
