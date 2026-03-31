from django.contrib import admin
from django.db import models
from .models import Mod, ModDependency, ModFile, ModFileGroup, ModImage

admin.site.register(Mod)
admin.site.register(ModDependency)
admin.site.register(ModFile)
admin.site.register(ModFileGroup)
admin.site.register(ModImage)
