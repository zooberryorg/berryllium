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


@login_required
@require_POST
def thumbnail(request, post_id):
    """Upload the post's one image. Returns the thumbnail card."""
    post = _editable_post(request, post_id)
    error = ""
    if request.POST.get("action") == "remove":
        if post.thumbnail:
            post.thumbnail.delete(save=False)
            post.thumbnail = None
            post.save(update_fields=["thumbnail", "last_updated"])
    else:
        form = ThumbnailForm(request.POST, request.FILES)
        if form.is_valid():
            if post.thumbnail:
                post.thumbnail.delete(save=False)
            post.thumbnail = form.cleaned_data["image"]
            post.save(update_fields=["thumbnail", "last_updated"])
        else:
            error = form.errors["image"][0]
    return render(request, "posts/editor/thumbnail.html", {"post": post, "thumbnail_error": error})

@login_required
@require_POST
def files(request, post_id):
    """Attach one or more files. Returns the files card."""
    post = _editable_post(request, post_id)
    errors = []
    uploads = request.FILES.getlist("files")
    room = MAX_POST_FILES - post.files.count()
    if len(uploads) > room:
        errors.append(f"A post can have at most {MAX_POST_FILES} files. Remove some first.")
        uploads = uploads[:max(room, 0)]
    order = post.files.count()
    for upload in uploads:
        problem = clean_post_file(upload)
        if problem:
            errors.append(problem)
            continue
        PostFile.objects.create(post=post, file=upload, filename=upload.name, size=upload.size, order=order)
        order += 1
    return render(request, "posts/editor/files.html", {
        "post": post, "files": post.files.all(), "file_errors": errors,
        "file_extensions": ", ".join("." + e for e in POST_FILE_EXTENSIONS), "max_files": MAX_POST_FILES,
    })

@login_required
@require_POST
def file_change(request, post_id, file_id):
    post = _editable_post(request, post_id)
    attachment = get_object_or_404(PostFile, pk=file_id, post=post)
    if request.POST.get("action") == "delete":
        attachment.delete()
    else:
        attachment.title = request.POST.get("title", "").strip()[:255]
        attachment.save(update_fields=["title"])
    return render(request, "posts/editor/files.html", {
        "post": post, "files": post.files.all(), "file_errors": [],
        "file_extensions": ", ".join("." + e for e in POST_FILE_EXTENSIONS), "max_files": MAX_POST_FILES,
    })

@login_required
@require_POST
def body_image(request, post_id):
    """Image button for editor"""
    post = _editable_post(request, post_id)
    form = PostImageForm(request.POST, request.FILES)
    if not form.is_valid():
        return JsonResponse({"error": form.errors["image"][0]}, status=400)
    image = PostImage.objects.create(post=post, image=form.cleaned_data["image"])
    return JsonResponse({"url": image.image.url})


@login_required
@require_POST
def preview(request, post_id):
    _editable_post(request, post_id)
    # the shared editor script sends the text as "description"
    html = render_markdown(request.POST.get("description", ""))
    return HttpResponse(html or '<p class="opacity-60">Nothing to preview yet.</p>')

# --------------------------------------------------------------------------- reading


@require_GET
def detail(request, post_id):
    post = get_object_or_404(Post.objects.select_related("uploaded_by"), pk=post_id)
    if not can_view(post, request.user):
        raise Http404("Post not found.")
    body_html, toc = render_markdown_with_toc(post.body)
    credits = list(post.credits.select_related("member", "author__member"))
    # related: same kind, most shared tags first, then newest
    tag_ids = list(post.tags.values_list("pk", flat=True))
    related = published_posts(post.kind).exclude(pk=post.pk).select_related("uploaded_by")
    if tag_ids:
        related = related.annotate(shared=Count("tags", filter=Q(tags__in=tag_ids))).order_by("-shared", "-publish_date")
    related = related[:3]
    return render(request, "posts/detail/base.html", {
        "post": post,
        "body_html": body_html,
        "toc": toc,
        "files": list(post.files.all()),
        "collaborators": [c for c in credits if c.role == ModCredit.Role.COLLABORATOR],
        "original_authors": [c for c in credits if c.role == ModCredit.Role.ORIGINAL_AUTHOR],
        "tags": list(post.tags.all()),
        "original_websites": list(post.original_websites.all()),
        "related": related,
        # "Updated" only when an edit came more than a day after publishing
        "was_updated": bool(post.first_published_at) and (post.last_updated - post.publish_date).total_seconds() > 86400,
        "is_public": is_public(post),
        "can_edit": can_edit_post(request.user, post),
        "explore_tab": "news" if post.kind == Post.Kind.NEWS else "tutorials",
    })

@require_GET
def download(request, file_id):
    attachment = get_object_or_404(PostFile.objects.select_related("post"), pk=file_id)
    if not can_view(attachment.post, request.user):
        raise Http404("File not found.")
    if is_public(attachment.post):
        PostFile.objects.filter(pk=attachment.pk).update(download_count=F("download_count") + 1)
    return FileResponse(attachment.file.open("rb"), as_attachment=True, filename=attachment.filename)


def _listing(request, kind, explore_tab):
    params = request.GET
    q = params.get("q", "").strip()[:100]
    tag = proper_case(params.get("tag", ""))[:50]
    sort = params.get("sort", "")
    sort = sort if sort in SORTS else "recent"
    posts = published_posts(kind).select_related("uploaded_by").prefetch_related("tags")
    if q:
        posts = posts.filter(Q(title__icontains=q) | Q(summary__icontains=q) | Q(tags__name__icontains=q)).distinct()
    if tag:
        posts = posts.filter(tags__name__iexact=tag)
    page = Paginator(posts.order_by(*SORTS[sort][1]), PAGE_SIZE).get_page(params.get("page"))
    page_query = params.copy()
    page_query.pop("page", None)
    context = {
        "page": page,
        "page_range": list(page.paginator.get_elided_page_range(page.number, on_each_side=1, on_ends=1)),
        "page_query": page_query.urlencode(),
        "q": q, "tag": tag, "sort": sort,
        "sort_options": [(key, label) for key, (label, _) in SORTS.items()],
        "kind": kind,
        "kind_label": dict(Post.Kind.choices)[kind],
        "explore_tab": explore_tab,
        "has_any": published_posts(kind).exists(),
    }
    is_htmx = request.headers.get("HX-Request") and not request.headers.get("HX-History-Restore-Request")
    return render(request, "posts/explore/results.html" if is_htmx else "posts/explore/base.html", context)


@require_GET
def explore_tutorials(request):
    return _listing(request, Post.Kind.TUTORIAL, "tutorials")


@require_GET
def explore_news(request):
    return _listing(request, Post.Kind.NEWS, "news")

# --------------------------------------------------------------------------- Settings > My posts


def _my_posts(user):
    return Post.objects.filter(uploaded_by=user)


@login_required
def settings_posts(request):
    from berryllium.users.settings_views import _nav  # the Settings menu
    posts = _my_posts(request.user).order_by("-last_updated")
    return render(request, "posts/settings/posts.html", {
        "posts": posts,
        "panel_nav": _nav(request, "settings_posts"),
        "noun": _noun(request.user),
    })

@login_required
@require_POST
def settings_posts_change(request, post_id):
    post = get_object_or_404(_my_posts(request.user), pk=post_id)
    action = request.POST.get("action")
    name = f"\u201c{post.title or 'Untitled post'}\u201d"
    if action == "unpublish" and not post.draft:
        post.draft = True
        post.save(update_fields=["draft"])
        messages.success(request, f"Moved {name} to drafts.")
    elif action == "publish" and post.draft:
        problems = publish_problems(post)
        if problems:
            messages.warning(request, f"{name} wasn't published: " + " ".join(p["message"] for p in problems))
        else:
            publish_post(post)
            messages.success(request, f"Published {name}.")
    elif action == "delete":
        post.delete()
        messages.success(request, f"Deleted {name}.")
    return redirect("settings_posts")