from django.shortcuts import render
from django.views.generic import CreateView, TemplateView, FormView, UpdateView

from berryllium.users.models import Member
from berryllium.users.forms import MemberRegistrationForm, MemberLoginForm

class MemberRegistration(CreateView):
    model = Member
    form_class = MemberRegistrationForm
    template_name = "users/register.html"
    success_url = "/"

    def form_valid(self, form):
        return super().form_valid(form)
    
class MemberLogin(FormView):
    form_class = MemberLoginForm
    template_name = "users/login.html"
    success_url = "/"