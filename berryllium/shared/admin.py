from django.contrib import admin

from berryllium.shared.models import ArchivedWebsite, ArchivedWebsiteLink, Language, License, Tag


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
