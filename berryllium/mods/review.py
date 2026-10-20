from django.urls import reverse
from django.utils import timezone

from berryllium.mods.models import ModCredit, ModFile, ModFileGroup, ModImage
from berryllium.mods.settings import EXPANSION_REQUIREMENTS, GAME_OPTIONS, MOD_CATEGORIES


def _labels(stored, choices):
    """ "animals, scripts" -> ["Animals", "Scripts"] using a settings choices list."""
    lookup = dict(choices)
    return [lookup.get(key.strip(), key.strip()) for key in (stored or "").split(",") if key.strip()]


def _issue(mod, step, message):
    return {"message": message, "url": reverse(step, kwargs={"mod_id": mod.pk})}


def review_issues(mod):
    """
    Returns a tuple of (problems, suggestions) for a mod. They are shown but don't block publishing.
    Each is {"message", "url"} where url is the step to fix it on.
    """
    problems, suggestions = [], []

    # General
    if not mod.title:
        problems.append(_issue(mod, "mod_create_general", "Add a title."))
    if not mod.summary:
        problems.append(_issue(mod, "mod_create_general", "Add a summary."))
    if not mod.thumbnail:
        problems.append(_issue(mod, "mod_create_general", "Add a thumbnail / logo."))
    if mod.is_archived_file:
        if not mod.original_release_date:
            problems.append(_issue(mod, "mod_create_general", "Archived mods need an original release date."))
        if not mod.original_websites.exists():
            problems.append(_issue(mod, "mod_create_general", "Archived mods need at least one original website."))
        if not mod.credits.filter(role=ModCredit.Role.ORIGINAL_AUTHOR).exists():
            problems.append(_issue(mod, "mod_create_general", "Archived mods need at least one original author."))

    # Categorization
    if not mod.category:
        problems.append(_issue(mod, "mod_create_categorization", "Choose at least one category."))
    if not mod.game:
        problems.append(_issue(mod, "mod_create_categorization", "Choose which game(s) the mod is for."))
    if not mod.expansions:
        problems.append(_issue(mod, "mod_create_categorization", "Choose the required expansions (or None)."))

    # Files
    if not (mod.files.exists() or (mod.is_external and mod.external_url)):
        problems.append(_issue(mod, "mod_create_files", "Upload at least one file."))
    # Images
    if not mod.images.exists():
        problems.append(_issue(mod, "mod_create_images", "Upload at least one image."))
    # Recommended    
    if not (mod.description or "").strip():
        suggestions.append(_issue(mod, "mod_create_description", "Add a description."))
    if not mod.licenses.exists():
        suggestions.append(_issue(mod, "mod_create_resources", "Pick a license so others know how they may use your work."))

    return problems, suggestions

def review_context(mod):
    """Show the mod's current state and any issues that need to be fixed before publishing."""
    images = list(ModImage.objects.filter(mod=mod))
    cover = next((image for image in images if image.is_cover), None)
    credits = list(mod.credits.select_related("member", "author"))
    problems, suggestions = review_issues(mod)

    return {
        "problems": problems,
        "suggestions": suggestions,
        "is_scheduled": mod.publish_date and mod.publish_date > timezone.now(),
        # general
        "collaborators": [c for c in credits if c.role == ModCredit.Role.COLLABORATOR],
        "original_authors": [c for c in credits if c.role == ModCredit.Role.ORIGINAL_AUTHOR],
        "original_websites": list(mod.original_websites.all()),
        # categorization
        "category_labels": _labels(mod.category, MOD_CATEGORIES),
        "game_labels": _labels(mod.game, GAME_OPTIONS),
        "expansion_labels": _labels(mod.expansions, EXPANSION_REQUIREMENTS),
        "tags": list(mod.tags.all()),
        "pending_tags": mod.pending_tags or [],
        # files
        "file_groups": [
            (group, list(ModFile.objects.filter(filegroup=group)))
            for group in ModFileGroup.objects.filter(mod=mod)
        ],
        # images
        "cover_image": cover,
        "gallery_images": [image for image in images if not image.is_cover],
        # resources
        "dependencies": list(mod.dependencies.select_related("ref")),
        "mod_licenses": list(mod.licenses.select_related("license")),
        "languages": list(mod.languages.all()),
        "attributions": list(mod.attributions.all()),
        "links": list(mod.links.all()),
    }
