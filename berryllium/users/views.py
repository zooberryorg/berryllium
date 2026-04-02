from django.shortcuts import render
from django.views.generic import CreateView, TemplateView, FormView, UpdateView
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth import login, logout

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

    def form_valid(self, form):
        user = form.get_user()
        login(self.request, user)
        if self.request.headers.get("HX-Request"):
            response = HttpResponse()
            response["HX-Redirect"] = reverse("home")
            return response
        return HttpResponseRedirect(reverse("home"))
    
    def form_invalid(self, form):
        response = super().form_invalid(form)
        response.status_code = 400
        # return the form with errors to be rendered in the template
        return response