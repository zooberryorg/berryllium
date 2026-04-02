from django.shortcuts import render
from django.views.generic import CreateView, TemplateView, FormView, UpdateView

from berryllium.users.models import Member


class MemberRegistration(CreateView):
    model = Member
    template_name = "users/register.html"
    success_url = "/"

    def form_valid(self, form):
        return super().form_valid(form)
    
