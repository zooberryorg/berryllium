from django.contrib import admin
from .models import Mod, Dependency, FileUpload, FileGroup, FileGroupMembership

# Register your models here.
admin.site.register(Mod)
admin.site.register(Dependency)
admin.site.register(FileUpload)
admin.site.register(FileGroup)
admin.site.register(FileGroupMembership)