from django.forms import CheckboxSelectMultiple


class PillCheckboxSelectMultiple(CheckboxSelectMultiple):
    """
    Custom checkbox design for Berryllium template.
    """
    template_name = "core/widgets/pill_checkbox_select.html"
    option_template_name = "core/widgets/pill_checkbox_option.html"
