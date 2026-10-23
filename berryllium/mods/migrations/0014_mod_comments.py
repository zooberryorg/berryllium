from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("mods", "0013_mod_first_published_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="mod",
            name="comment_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="mod",
            name="comments_enabled",
            field=models.BooleanField(default=True),
        ),
    ]
