from django.forms import ModelForm

from berryllium.users.models import Member


class MemberRegistrationForm(ModelForm):
    class Meta:
        model = Member
        fields = ["username", "email", "password"]

class MemberLoginForm(ModelForm):
    class Meta:
        model = Member
        fields = ["username", "password"]