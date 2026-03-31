from django.contrib import admin
from .models import Mod, ModDependency, ModFile, ModFileGroup, ModImage

# Register your models here.
admin.site.register(Mod)
admin.site.register(ModDependency)
admin.site.register(ModFile)
admin.site.register(ModFileGroup)
admin.site.register(ModImage)
