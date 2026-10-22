from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET
from django.views.generic import CreateView, TemplateView, FormView, UpdateView
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout

from berryllium.users.models import Author, Member
from berryllium.users.profiles import author_mods, member_mods, profile_context
from berryllium.users.forms import MemberRegistrationForm, MemberLoginForm

class MemberRegistration(CreateView):
    model = Member
    form_class = MemberRegistrationForm
    template_name = "users/register.html"
    success_url = "/"

    def form_valid(self, form):
        self.object = form.save()
        login(self.request, self.object)
        if self.request.headers.get("HX-Request"):
            response = HttpResponse()
            response["HX-Redirect"] = reverse("home")
            return response
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        return render(self.request, "users/fields.html", {"form": form})
    
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

# --------------------------------------------------------------------------- profiles

def _render_profile(request, context):
    """Full page, or just the mod results when the search / sort / page changes (htmx)."""
    is_htmx = request.headers.get("HX-Request") and not request.headers.get("HX-History-Restore-Request")
    template = "users/profile/results.html" if is_htmx else "users/profile/base.html"
    return render(request, template, context)

@require_GET
def member_profile(request, username):
    # an exact match wins and redirect to the URL with the real spelling
    members = Member.objects.filter(is_active=True)
    member = members.filter(username=username).first() or members.filter(username__iexact=username.strip()).order_by("pk").first()
    if member is None:
        raise Http404("Member not found.")
    if member.username != username:
        return redirect("member_profile", username=member.username)
    context = profile_context(request, member_mods(member))
    context.update({"member": member, "display_name": member.username, "is_own_profile": request.user == member})
    return _render_profile(request, context)

@require_GET
def author_profile(request, author_id):
    """Authors without an account. Once an Author is linked to a member, their member page is the profile"""
    author = get_object_or_404(Author.objects.select_related("member"), pk=author_id)
    if author.member_id:
        return redirect("member_profile", username=author.member.username)
    context = profile_context(request, author_mods(author))
    context.update({"author": author, "display_name": author.name})
    return _render_profile(request, context)
