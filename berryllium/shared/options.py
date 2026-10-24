from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

CACHE_KEY = "berryllium-site-options"
CACHE_SECONDS = 300
NOT_APPLICABLE = "na"  # the game choice meaning "not for one game"
NO_EXPANSION = "none"


def _load():
    data = cache.get(CACHE_KEY)
    if data is None:
        from berryllium.shared.models import Category, Expansion, Game

        data = {
            "mod": [(c.key, c.label, c.icon, c.is_active) for c in Category.objects.filter(scope=Category.Scope.MOD)],
            "article": [(c.key, c.label, c.icon, c.is_active) for c in Category.objects.filter(scope=Category.Scope.ARTICLE)],
            "games": [(g.key, g.label, g.is_active) for g in Game.objects.all()],
            "expansions": [(e.key, e.label, e.is_active) for e in Expansion.objects.all()],
        }
        cache.set(CACHE_KEY, data, CACHE_SECONDS)
    return data


def clear():
    cache.delete(CACHE_KEY)


# --------------------------------------------------------------------------- choices (active ones, in order)


def mod_categories():
    return [(key, label) for key, label, _, active in _load()["mod"] if active]


def article_categories():
    return [(key, label) for key, label, _, active in _load()["article"] if active]


def game_options(include_na=True):
    return [(key, label) for key, label, active in _load()["games"] if active and (include_na or key != NOT_APPLICABLE)]


def expansion_options():
    return [(key, label) for key, label, active in _load()["expansions"] if active]


# --------------------------------------------------------------------------- labels and icons (every one, active or not)


def category_labels(scope="mod"):
    return {key: label for key, label, _, _ in _load()[scope]}


def category_icons(scope="mod"):
    return {key: icon for key, _, icon, _ in _load()[scope]}


def game_labels():
    return {key: label for key, label, _ in _load()["games"]}


def expansion_labels():
    return {key: label for key, label, _ in _load()["expansions"]}


def keys(stored):
    """ "animals, scripts" -> ["animals", "scripts"] """
    return [key.strip() for key in (stored or "").split(",") if key.strip()]


def labels_for(stored, label_map):
    return [label_map.get(key, key) for key in keys(stored)]


def category_chips(stored, scope="mod"):
    names, icons = category_labels(scope), category_icons(scope)
    return [{"key": key, "label": names.get(key, key), "icon": icons.get(key, "bi-folder")} for key in keys(stored)]


@receiver([post_save, post_delete], dispatch_uid="clear-site-options")
def _clear_on_change(sender, **kwargs):
    if sender.__name__ in ("Category", "Game", "Expansion") and sender._meta.app_label == "shared":
        clear()
