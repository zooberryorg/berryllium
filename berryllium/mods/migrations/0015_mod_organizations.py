import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mods", "0014_mod_comments"),
        ("organizations", "0002_organization_pages_and_roles"),
    ]

    operations = [
        migrations.AddField(
            model_name="mod",
            name="organization",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="mods",
                to="organizations.organization",
            ),
        ),
    ]