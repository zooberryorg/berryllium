from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("posts", "0004_post_organization"),
    ]

    operations = [
        migrations.AddField(
            model_name="post",
            name="category",
            field=models.CharField(blank=True, db_index=True, max_length=200),
        ),
        migrations.AddField(
            model_name="post",
            name="expansions",
            field=models.CharField(blank=True, max_length=200),
        ),
    ]
