from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0002_organization_pages_and_roles"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="is_archived",
            field=models.BooleanField(db_index=True, default=False),
        ),
    ]
