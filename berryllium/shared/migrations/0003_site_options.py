import django.db.models.deletion
from django.db import migrations, models


MOD_CATEGORIES = [
    ("animals", "Animals", "bi-emoji-smile"),
    ("animal_needs", "Animal Needs", "bi-heart-fill"),
    ("props_and_structures", "Props & Structures", "bi-building"),
    ("packs", "Packs", "bi-box-seam"),
    ("utilities", "Utilities", "bi-tools"),
    ("texture_variants", "Texture Variants", "bi-palette"),
    ("texture_replacements", "Texture Replacements", "bi-image"),
    ("gameplay_tweaks", "Gameplay Tweaks", "bi-gear-fill"),
    ("remakes", "Remakes", "bi-arrow-clockwise"),
    ("scripts", "Scripts", "bi-code-slash"),
    ("zoos_and_saves", "Zoos & Saves", "bi-map"),
    ("assets", "Assets", "bi-archive"),
]
ARTICLE_CATEGORIES = [
    ("getting_started", "Getting Started", "bi-signpost-2"),
    ("installing_mods", "Installing Mods", "bi-download"),
    ("modelling", "Modelling", "bi-box"),
    ("texturing", "Texturing", "bi-palette"),
    ("animals", "Animals", "bi-emoji-smile"),
    ("scenery", "Objects & Scenery", "bi-tree"),
    ("zoo_building", "Zoo Building", "bi-map"),
    ("scripting", "Scripting", "bi-code-slash"),
    ("tools", "Tools", "bi-tools"),
    ("troubleshooting", "Troubleshooting", "bi-wrench-adjustable"),
    ("announcements", "Announcements", "bi-megaphone"),
    ("community", "Community", "bi-people"),
]
GAMES = [("na", "Not Applicable"), ("zt1", "Zoo Tycoon 1"), ("zt2", "Zoo Tycoon 2")]
EXPANSIONS = [
    ("none", "None", None),
    ("mm1", "Marine Mania", "zt1"),
    ("dd", "Dinosaur Digs", "zt1"),
    ("aa", "African Adventure", "zt2"),
    ("es", "Endangered Species", "zt2"),
    ("mm2", "Marine Mania 2", "zt2"),
    ("ea", "Extinct Animals", "zt2"),
]


def seed(apps, schema_editor):
    """The lists that used to be fixed in mods/settings.py, plus a starting list of article categories."""
    Category = apps.get_model("shared", "Category")
    Game = apps.get_model("shared", "Game")
    Expansion = apps.get_model("shared", "Expansion")
    for scope, rows in (("mod", MOD_CATEGORIES), ("article", ARTICLE_CATEGORIES)):
        for order, (key, label, icon) in enumerate(rows):
            Category.objects.get_or_create(
                scope=scope,
                key=key,
                defaults={"label": label, "icon": icon, "order": order},
            )
    games = {}
    for order, (key, label) in enumerate(GAMES):
        games[key], _ = Game.objects.get_or_create(
            key=key, defaults={"label": label, "order": order}
        )
    for order, (key, label, game) in enumerate(EXPANSIONS):
        Expansion.objects.get_or_create(
            key=key, defaults={"label": label, "order": order, "game": games.get(game)}
        )


class Migration(migrations.Migration):
    dependencies = [
        ("shared", "0002_language_license"),
    ]

    operations = [
        migrations.CreateModel(
            name="Game",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "key",
                    models.SlugField(
                        help_text="Saved on mods and articles. Don't change it once it's in use.",
                        max_length=30,
                        unique=True,
                    ),
                ),
                ("label", models.CharField(max_length=80)),
                ("order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "ordering": ["order", "label"],
            },
        ),
        migrations.CreateModel(
            name="Category",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "scope",
                    models.CharField(
                        choices=[("mod", "Mods"), ("article", "Articles")],
                        db_index=True,
                        default="mod",
                        max_length=10,
                    ),
                ),
                (
                    "key",
                    models.SlugField(
                        help_text="Saved on mods and articles. Don't change it once it's in use."
                    ),
                ),
                ("label", models.CharField(max_length=80)),
                (
                    "icon",
                    models.CharField(
                        default="bi-folder",
                        help_text="A Bootstrap icon class, e.g. bi-map.",
                        max_length=50,
                    ),
                ),
                ("order", models.PositiveIntegerField(default=0)),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Offered in forms and filters. Turn off instead of deleting.",
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "categories",
                "ordering": ["scope", "order", "label"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("scope", "key"), name="category_key_per_scope"
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="Expansion",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "key",
                    models.SlugField(
                        help_text="Saved on mods and articles. Don't change it once it's in use.",
                        max_length=30,
                        unique=True,
                    ),
                ),
                ("label", models.CharField(max_length=80)),
                ("order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "game",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="expansions",
                        to="shared.game",
                    ),
                ),
            ],
            options={
                "ordering": ["order", "label"],
            },
        ),
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
