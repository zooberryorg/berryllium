from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, F, Q
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from berryllium.mods.models import ModCredit
from berryllium.posts.forms import (
    MAX_POST_FILES,
    POST_FILE_EXTENSIONS,
    PostEditorForm,
    PostGeneralForm,
    PostImageForm,
    ThumbnailForm,
    clean_post_file,
)
from berryllium.posts.models import Post, PostFile, PostImage
from berryllium.posts.services import can_view, is_public, publish_post, publish_problems, published_posts
from berryllium.shared.fields import proper_case
from berryllium.shared.markdown_render import render_markdown, render_markdown_with_toc
from berryllium.users.permissions import can_edit_post, can_post_news

PAGE_SIZE = 12
SORTS = {"recent": ("Newest", ["-publish_date"]), "updated": ("Recently updated", ["-last_updated"]), "title": ("Title (A–Z)", ["title"])}


def _editable_post(request, post_id):
    post = get_object_or_404(Post.objects.select_related("uploaded_by"), pk=post_id)
    if not can_edit_post(request.user, post):
        raise Http404("Post not found.")
    return post


def _noun(user):
    """"Post" for the site team (they pick the kind) or "Tutorial" for regular members (they can only post tutorials)."""
    return "Post" if can_post_news(user) else "Tutorial"

# --------------------------------------------------------------------------- create (modal)


@login_required
@require_http_methods(["GET", "POST"])
def create_draft(request):
    form = PostGeneralForm(request.POST or None, uploader=request.user, can_post_news=can_post_news(request.user))
    if request.method == "POST" and form.is_valid():
        post = form.save(commit=False)
        post.uploaded_by = request.user
        post.save()
        form.save_m2m()
        form.save_relations()
        response = HttpResponse()
        response["HX-Redirect"] = reverse("post_edit", kwargs={"post_id": post.pk})
        return response
    return render(request, "posts/create/draft.html", {"form": form, "noun": _noun(request.user)})

# --------------------------------------------------------------------------- editor


@login_required
@require_http_methods(["GET", "POST"])
def edit(request, post_id):
    post = _editable_post(request, post_id)
    form_kwargs = {"instance": post, "uploader": post.uploaded_by, "can_post_news": can_post_news(request.user), "user": request.user}
    if request.method == "POST":
        action = request.POST.get("action", "save")
        form = PostEditorForm(request.POST, **form_kwargs)
        saved = form.is_valid()
        if saved:
            form.save()
            form.save_relations()
        if action == "autosave":
            errors = [message for field_errors in form.errors.values() for message in field_errors]
            return JsonResponse({"saved": saved, "errors": errors[:3]})
        if saved and action == "publish":
            problems = publish_problems(post)
            if not problems:
                was_live = post.first_published_at is not None
                publish_post(post)
                messages.success(request, "Changes saved." if was_live else "Published.")
                return redirect("post_detail", post_id=post.pk)
            messages.error(request, "Fix the items in Publishing before publishing.")
        elif saved:
            messages.success(request, "Saved.")
            return redirect("post_edit", post_id=post.pk)
        else:
            messages.error(request, "Some fields need fixing. They're marked below.")
    else:
        form = PostEditorForm(**form_kwargs)
    return render(request, "posts/editor/base.html", {
        "form": form,
        "post": post,
        "problems": publish_problems(post),
        "files": post.files.all(),
        "file_extensions": ", ".join("." + e for e in POST_FILE_EXTENSIONS),
        "max_files": MAX_POST_FILES,
        "noun": post.get_kind_display(),
    })

