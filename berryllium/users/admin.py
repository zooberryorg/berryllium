from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from berryllium.users.models import Member, Author

@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ("name", "member", "created_at")
    search_fields = ("name", "member__username")
    raw_id_fields = ("member",)

@admin.register(Member)
class MemberAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Preferences", {"fields": ("date_format", "time_format")}),
    )