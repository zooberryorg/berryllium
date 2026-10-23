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