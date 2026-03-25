from django.contrib import admin
from .models import Mod, ModDependency, ModFile, ModFileGroup

# Register your models here.
admin.site.register(Mod)
admin.site.register(ModDependency)
admin.site.register(ModFile)
admin.site.register(ModFileGroup)
