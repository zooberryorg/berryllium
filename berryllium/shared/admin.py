from django.contrib import admin

from berryllium.shared.models import (
    ArchivedWebsite,
    ArchivedWebsiteLink,
    Category,
    Expansion,
    Game,
    Language,
    License,
    Tag,
)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ("name",)


class ArchivedWebsiteLinkInline(admin.TabularInline):
    model = ArchivedWebsiteLink
    extra = 1


@admin.register(ArchivedWebsite)
class ArchivedWebsiteAdmin(admin.ModelAdmin):
    list_display = ("name", "is_offline", "is_enabled", "est_date", "closure_date")
    list_filter = ("is_offline", "is_enabled")
    search_fields = ("name", "aliases")
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("former_staff",)
    inlines = [ArchivedWebsiteLinkInline]


@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    list_display = ("name", "short_name", "is_enabled")
    list_filter = ("is_enabled",)
    search_fields = ("name", "short_name", "description")


@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ("name", "code")
    search_fields = ("name", "code")


# --------------------------------------------------------------------------- options shown in forms and filters
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("key", "label", "scope", "icon", "order", "is_active")
    list_editable = ("label", "icon", "order", "is_active")
    list_filter = ("scope", "is_active")
    search_fields = ("label", "key")
    prepopulated_fields = {"key": ("label",)}


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ("label", "key", "order", "is_active")
    list_editable = ("order", "is_active")
    prepopulated_fields = {"key": ("label",)}


@admin.register(Expansion)
class ExpansionAdmin(admin.ModelAdmin):
    list_display = ("label", "key", "game", "order", "is_active")
    list_editable = ("order", "is_active")
    list_filter = ("game", "is_active")
    prepopulated_fields = {"key": ("label",)}
