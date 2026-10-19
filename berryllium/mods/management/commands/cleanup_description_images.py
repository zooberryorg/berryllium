from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from berryllium.mods.models import ModDescriptionImage


class Command(BaseCommand):
    help = "Delete description images older than 24 hours that their mod's description no longer uses."

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(hours=24)
        removed = 0
        for img in ModDescriptionImage.objects.filter(uploaded_at__lt=cutoff).select_related("mod"):
            if img.image.url not in (img.mod.description or ""):
                img.delete()
                removed += 1
        self.stdout.write(f"Removed {removed} unused description image(s).")