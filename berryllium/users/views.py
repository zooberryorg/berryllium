from django.shortcuts import render
from django.views.generic import CreateView, TemplateView, FormView, UpdateView
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout

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
        username = form.cleaned_data["username"]
        password = form.cleaned_data["password"]
        user = authenticate(self.request, username=username, password=password)
        if user is not None:
            login(self.request, user)
            if self.request.headers.get("HX-Request"):
                response = HttpResponse()
                response["HX-Redirect"] = reverse("home")
                return response
            return HttpResponseRedirect(reverse("home"))
        else:
            form.add_error(None, "Invalid username or password.")
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        if self.request.headers.get("HX-Request"):
            return render(self.request, "users/fields.html", {"form": form}, status=200)
        return render(self.request, "users/fields.html", {"form": form}, status=200)
