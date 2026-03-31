from django.contrib import admin
from .models import Mod, ModDependency, ModFile, ModFileGroup, ModImage
from markdownx.admin import MarkdownxModelAdmin

# Register your models here.
admin.site.register(Mod, MarkdownxModelAdmin)
admin.site.register(ModDependency)
admin.site.register(ModFile)
admin.site.register(ModFileGroup)
admin.site.register(ModImage)
