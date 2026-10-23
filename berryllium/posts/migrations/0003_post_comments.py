from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("posts", "0002_post_game"),
    ]

    operations = [
        migrations.AddField(
            model_name="post",
            name="comment_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="post",
            name="comments_enabled",
            field=models.BooleanField(default=True),
        ),
    ]