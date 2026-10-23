import os

from django import forms
from django.urls import reverse

from berryllium.mods.forms import DescriptionImageForm, ModGeneralInfoForm
from berryllium.mods.pickers import PickerField, picker_config, resolve_tags, tag_items
from berryllium.mods.settings import ALLOWED_EXTENSIONS, GAME_OPTIONS, MAX_FILE_SIZE, MAX_IMAGE_SIZE
from berryllium.posts.models import Post
from berryllium.shared.widgets import PillCheckboxSelectMultiple

PostImageForm = DescriptionImageForm

POST_FILE_EXTENSIONS = [*ALLOWED_EXTENSIONS, "pdf"]
MAX_POST_FILES = 20
MIN_THUMBNAIL_WIDTH = 640


class PostGeneralForm(ModGeneralInfoForm):
    kind = forms.ChoiceField(choices=Post.Kind.choices, widget=forms.RadioSelect, initial=Post.Kind.TUTORIAL)

    class Meta(ModGeneralInfoForm.Meta):
        model = Post
        fields = ["kind", *ModGeneralInfoForm.Meta.fields]

    def __init__(self, *args, can_post_news=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.can_post_news = can_post_news
        if not can_post_news:
            # members only write tutorials; the choice isn't shown
            del self.fields["kind"]
        # wording for posts instead of mods
        self.fields["title"].widget.attrs["placeholder"] = "Enter a title..."
        self.fields["summary"].widget.attrs["placeholder"] = "One or two sentences shown on cards and under the title..."
        self.fields["collaborators"].help_text = "People who wrote this with you."
        self.fields["original_authors"].help_text = "Who wrote it originally."
        self.fields["is_archived_file"].label = "Was this first published somewhere else?"


class PostEditorForm(PostGeneralForm):
    """The editor: everything from the modal, plus tags and the article body (markdown)."""

    tags = PickerField(required=False, allow_new=True, max_items=20, label="Tags")
    game = forms.MultipleChoiceField(
        required=False,
        label="Game",
        choices=[option for option in GAME_OPTIONS if option[0] != "na"],
        widget=PillCheckboxSelectMultiple,
    )
    body = forms.CharField(
        required=False,
        label="Article",
        widget=forms.Textarea(attrs={
            "placeholder": "Write your article in markdown. Headings (## Heading) become the table of contents.",
            "class": "zb-textarea text-sm resize-y w-full font-mono",
            "rows": 22,
        }),
    )

    class Meta(PostGeneralForm.Meta):
        fields = [*PostGeneralForm.Meta.fields, "game", "body"]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if isinstance(self.initial.get("game"), str):
            self.initial["game"] = [key.strip() for key in self.initial["game"].split(",") if key.strip()]
            
    def clean_game(self):
        return ", ".join(self.cleaned_data.get("game") or [])

    def clean_tags(self):
        return resolve_tags(self.cleaned_data.get("tags", []))

    def save_relations(self):
        super().save_relations()
        existing, new_names = self.cleaned_data["tags"]
        post = self.instance
        post.tags.set(existing)
        # new tags are created when the post is published, as for mods
        post.pending_tags = new_names
        post.save(update_fields=["pending_tags"])

    def tags_picker(self):
        if self.is_bound:
            existing, new_names = resolve_tags([v for v in self.data.getlist(self.add_prefix("tags")) if v], strict=False)
        else:
            existing = list(self.instance.tags.all()) if self.instance.pk else []
            new_names = list(self.instance.pending_tags or [])
        return picker_config(
            name=self.add_prefix("tags"),
            search_url=reverse("search_tags"),
            items=tag_items(existing, new_names),
            title="Add tags",
            placeholder="Search tags...",
            allow_new=True,
        )


class ThumbnailForm(forms.Form):
    image = forms.ImageField()

    def clean_image(self):
        image = self.cleaned_data["image"]
        if image.size > MAX_IMAGE_SIZE:
            raise forms.ValidationError(f"The image must be under {MAX_IMAGE_SIZE // (1024 * 1024)} MB.")
        if image.image.format not in ("JPEG", "PNG", "WEBP"):
            raise forms.ValidationError("Use a JPG, PNG or WEBP image.")
        width, _ = image.image.size
        if width < MIN_THUMBNAIL_WIDTH:
            raise forms.ValidationError(f"The image must be at least {MIN_THUMBNAIL_WIDTH}px wide (yours is {width}px).")
        return image


def clean_post_file(upload):
    extension = os.path.splitext(upload.name)[1].lower().lstrip(".")
    if extension not in POST_FILE_EXTENSIONS:
        return f"{upload.name}: only {', '.join('.' + e for e in POST_FILE_EXTENSIONS)} files can be attached."
    if upload.size > MAX_FILE_SIZE:
        return f"{upload.name}: files must be under {MAX_FILE_SIZE // (1024 * 1024)} MB."
    return ""
