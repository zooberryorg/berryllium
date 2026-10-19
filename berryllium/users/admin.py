from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from berryllium.users.models import Member, Author

admin.site.register(Member, UserAdmin)

@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ("name", "member", "created_at")
    search_fields = ("name", "member__username")
    raw_id_fields = ("member",)