import json
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from berryllium.comments import services, targets
from berryllium.comments.forms import CommentForm
from berryllium.comments.models import Comment, UploadedImage
from berryllium.mods.forms import DescriptionImageForm
from berryllium.shared.markdown_render import render_markdown
from berryllium.users.permissions import is_moderator

DAILY_IMAGE_LIMIT = 30


# --------------------------------------------------------------------------- context


def section_context(request, obj, page_number=1):
    """Everything the comment templates read, under one name (comments) so it can't clash with a page's own context."""
    user = request.user
    page = services.threads_page(obj, page_number)
    target_url = targets.url(obj)
    return {
        "target": obj,
        "kind": targets.kind_of(obj),
        "label": targets.label(obj),
        "url": target_url,
        "page": page,
        "count": obj.comment_count,
        "is_public": targets.is_public(obj),
        "enabled": obj.comments_enabled,
        "can_comment": services.can_comment(obj, user),
        "can_manage": targets.can_manage(obj, user),
        "is_moderator": is_moderator(user),
        "owner_ids": {member.pk for member in targets.owners(obj)},
        "login_url": f"{reverse('login')}?next={target_url}%23comments",
        "form": _new_form(),  # the top-level form; replaced by the submitted one when it has errors
    }


def _new_form(data=None):
    return CommentForm(data, auto_id="id_comment_%s")


def _section(request, obj, form=None, error=""):
    comments = section_context(request, obj)
    if form is not None:
        comments["form"] = form
    return render(request, "comments/section.html", {"comments": comments, "form_error": error})


def _thread(request, obj, thread_id, reply_form=None, reply_to=None, quote=None, error=""):
    comments = section_context(request, obj)
    thread = services.get_thread(thread_id)
    return render(request, "comments/thread.html", {
        "comments": comments, "thread": thread, "oob_count": True,
        "reply_form": reply_form, "reply_to": reply_to, "quote": quote, "form_error": error,
    })


def _posted(response, comment):
    """Tell the page which comment to scroll to."""
    response["HX-Trigger"] = json.dumps({"commentPosted": {"id": comment.pk}})
    return response


def _comment_on(obj, pk):
    """A comment on this target that can be answered or quoted."""
    if not pk or not str(pk).isdigit():
        return None
    comment = services.comments_for(obj).select_related("author", "parent").filter(pk=int(pk), is_deleted=False).first()
    if comment is None:
        raise Http404("That comment is gone.")
    return comment


def _editable(request, comment_id):
    comment = get_object_or_404(Comment.objects.select_related("author"), pk=comment_id)
    obj = comment.target
    if obj is None or not targets.can_view(obj, request.user):
        raise Http404("Comment not found.")
    return comment, obj

# --------------------------------------------------------------------------- reading


@require_GET
def more(request, kind, pk):
    """The "Show more comments" button: the next page of threads, plus the next button."""
    obj = targets.get_target(kind, pk)
    if not targets.can_view(obj, request.user):
        raise Http404("Not found.")
    comments = section_context(request, obj, request.GET.get("page", 1))
    return render(request, "comments/list.html", {"comments": comments})

# --------------------------------------------------------------------------- posting


@login_required
@require_POST
def create(request, kind, pk):
    obj = targets.get_target(kind, pk)
    if not targets.can_view(obj, request.user):
        raise Http404("Not found.")
    reply_to = _comment_on(obj, request.POST.get("reply_to"))
    quote = _comment_on(obj, request.POST.get("quote"))
    # a reply form keeps its own ids, so it doesn't clash with the main form on the page
    form = CommentForm(request.POST, auto_id=f"id_reply_{reply_to.thread_id}_%s" if reply_to else "id_comment_%s", rows=4 if reply_to else None)

    def failed(message=""):
        if reply_to is not None:
            return _thread(request, obj, reply_to.thread_id, reply_form=form, reply_to=reply_to, quote=quote, error=message)
        return _section(request, obj, form=form, error=message)

    if not services.can_comment(obj, request.user):
        return failed(f"Comments are turned off for this {targets.label(obj)}.")
    if not form.is_valid():
        return failed()
    if services.too_soon(request.user):
        return failed("You're commenting very quickly. Wait a few seconds and try again.")

    comment = services.create_comment(obj, request.user, form.cleaned_data["body"], reply_to=reply_to, quote=quote)
    if reply_to is not None:
        return _posted(_thread(request, obj, comment.thread_id), comment)
    return _posted(_section(request, obj), comment)

@login_required
@require_GET
def reply_form(request, comment_id):
    """The form under a thread, for Reply (no quote) or Quote (?quote=1)."""
    comment, obj = _editable(request, comment_id)
    if comment.is_deleted or not services.can_comment(obj, request.user):
        return HttpResponse("")
    quote = comment if request.GET.get("quote") else None
    form = CommentForm(auto_id=f"id_reply_{comment.thread_id}_%s", rows=4, placeholder=f"Reply to {comment.author.username if comment.author else 'this comment'}...")
    return render(request, "comments/form.html", {
        "comments": section_context(request, obj), "form": form, "mode": "reply",
        "thread_id": comment.thread_id, "reply_to": comment, "quote": quote,
    })

@login_required
@require_http_methods(["GET", "POST"])
def edit(request, comment_id):
    comment, obj = _editable(request, comment_id)
    comments = section_context(request, obj)
    if request.method == "GET" and request.GET.get("cancel"):
        return render(request, "comments/comment.html", {"comments": comments, "comment": comment})
    if not services.can_edit(comment, request.user):
        raise PermissionDenied
    form = CommentForm(request.POST or None, initial={"body": comment.body}, auto_id=f"id_edit_{comment.pk}_%s")
    if request.method == "POST" and form.is_valid():
        comment.body = form.cleaned_data["body"]
        comment.edited_at = timezone.now()
        comment.save(update_fields=["body", "edited_at"])
        return render(request, "comments/comment.html", {"comments": comments, "comment": comment})
    return render(request, "comments/form.html", {"comments": comments, "form": form, "mode": "edit", "comment": comment})

@login_required
@require_POST
def delete(request, comment_id):
    comment, obj = _editable(request, comment_id)
    if not services.can_delete(comment, request.user):
        raise PermissionDenied
    thread_id = comment.thread_id
    services.delete_comment(comment, request.user)
    obj.refresh_from_db(fields=["comment_count"])
    # the thread may be gone entirely then only the counter is sent
    return _thread(request, obj, thread_id)

@login_required
@require_POST
def toggle(request, kind, pk):
    """Turn comments off or on for a mod or post."""
    obj = targets.get_target(kind, pk)
    if not targets.can_manage(obj, request.user):
        raise PermissionDenied
    obj.comments_enabled = not obj.comments_enabled
    type(obj).objects.filter(pk=obj.pk).update(comments_enabled=obj.comments_enabled)
    return _section(request, obj)

# --------------------------------------------------------------------------- editor helpers (comments and messages)


@login_required
@require_POST
def preview(request):
    # the shared editor script sends the text as "description"
    html = render_markdown(request.POST.get("description", ""))
    return HttpResponse(html or '<p class="opacity-60">Nothing to preview yet.</p>')