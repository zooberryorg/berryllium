from django.forms import CheckboxSelectMultiple


class PillCheckboxSelectMultiple(CheckboxSelectMultiple):
    template_name = "core/widgets/pill_checkbox_select.html"
    option_template_name = "core/widgets/pill_checkbox_option.html"
