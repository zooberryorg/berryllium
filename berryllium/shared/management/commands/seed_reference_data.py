# fills the database with starter reference data for licenses and languages
from django.core.management.base import BaseCommand

from berryllium.shared.models import Language, License

LICENSES = [
    ("All Rights Reserved", "All rights reserved",
     "No permission is given to reuse, modify or redistribute without asking the author.", ""),
    ("Creative Commons Zero 1.0", "CC0 1.0",
     "Public domain dedication: anyone may use it for anything, no credit required.",
     "https://creativecommons.org/publicdomain/zero/1.0/"),
    ("Creative Commons Attribution 4.0", "CC BY 4.0",
     "Anyone may share and adapt it, even commercially, as long as they give credit.",
     "https://creativecommons.org/licenses/by/4.0/"),
    ("Creative Commons Attribution-ShareAlike 4.0", "CC BY-SA 4.0",
     "Share and adapt with credit; adaptations must use the same license.",
     "https://creativecommons.org/licenses/by-sa/4.0/"),
    ("Creative Commons Attribution-NonCommercial 4.0", "CC BY-NC 4.0",
     "Share and adapt with credit, but not for commercial purposes.",
     "https://creativecommons.org/licenses/by-nc/4.0/"),
    ("Creative Commons Attribution-NonCommercial-ShareAlike 4.0", "CC BY-NC-SA 4.0",
     "Share and adapt with credit, non-commercially, under the same license.",
     "https://creativecommons.org/licenses/by-nc-sa/4.0/"),
    ("Creative Commons Attribution-NoDerivatives 4.0", "CC BY-ND 4.0",
     "Share unchanged with credit, even commercially; no modified versions.",
     "https://creativecommons.org/licenses/by-nd/4.0/"),
    ("Creative Commons Attribution-NonCommercial-NoDerivatives 4.0", "CC BY-NC-ND 4.0",
     "Share unchanged with credit, non-commercially; no modified versions.",
     "https://creativecommons.org/licenses/by-nc-nd/4.0/"),
    ("MIT License", "MIT",
     "Permissive software license: reuse freely, keep the copyright notice.",
     "https://opensource.org/license/mit"),
    ("GNU General Public License v3.0", "GPL-3.0",
     "Copyleft software license: modified versions must be released under the GPL too.",
     "https://www.gnu.org/licenses/gpl-3.0.html"),
    ("Apache License 2.0", "Apache-2.0",
     "Permissive software license with an explicit patent grant.",
     "https://www.apache.org/licenses/LICENSE-2.0"),
]

LANGUAGES = [
    ("en", "English"), ("es", "Spanish"), ("fr", "French"), ("de", "German"),
    ("it", "Italian"), ("pt", "Portuguese"), ("pt-BR", "Portuguese (Brazil)"),
    ("nl", "Dutch"), ("pl", "Polish"), ("ru", "Russian"), ("cs", "Czech"),
    ("hu", "Hungarian"), ("sv", "Swedish"), ("da", "Danish"), ("no", "Norwegian"),
    ("fi", "Finnish"), ("tr", "Turkish"), ("ja", "Japanese"), ("ko", "Korean"),
    ("zh-Hans", "Chinese (Simplified)"), ("zh-Hant", "Chinese (Traditional)"),
]


class Command(BaseCommand):
    help = "Create or update starter licenses and languages."

    def handle(self, *args, **options):
        for name, short_name, description, url in LICENSES:
            License.objects.update_or_create(
                name=name, defaults={"short_name": short_name, "description": description, "url": url}
            )
        for code, name in LANGUAGES:
            Language.objects.update_or_create(code=code, defaults={"name": name})
        self.stdout.write(self.style.SUCCESS(f"{len(LICENSES)} licenses and {len(LANGUAGES)} languages ready."))