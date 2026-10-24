import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0002_organization_pages_and_roles"),
        ("posts", "0003_post_comments"),
    ]

    operations = [
        migrations.AddField(
            model_name="post",
            name="organization",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="posts",
                to="organizations.organization",
            ),
        ),
    ]