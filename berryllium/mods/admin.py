from django.contrib import admin
from .models import Mod, Dependency, ModFile, ModFileGroup

# Register your models here.
admin.site.register(Mod)
admin.site.register(Dependency)
admin.site.register(ModFile)
admin.site.register(ModFileGroup)
