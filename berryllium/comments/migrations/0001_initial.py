import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import berryllium.comments.models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Comment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("object_id", models.PositiveBigIntegerField()),
                ("reply_to_name", models.CharField(blank=True, max_length=150)),
                ("quote_author", models.CharField(blank=True, max_length=150)),
                ("quote_text", models.TextField(blank=True)),
                ("body", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("edited_at", models.DateTimeField(blank=True, null=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("deleted_by_moderator", models.BooleanField(default=False)),
                ("author", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="comments", to=settings.AUTH_USER_MODEL)),
                ("content_type", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="contenttypes.contenttype")),
                ("parent", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="replies", to="comments.comment")),
                ("quote_of", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="comments.comment")),
                ("reply_to", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="comments.comment")),
            ],
            options={
                "ordering": ["created_at"],
                "indexes": [models.Index(fields=["content_type", "object_id", "parent"], name="comment_target_parent_idx")],
            },
        ),
        migrations.CreateModel(
            name="UploadedImage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to=berryllium.comments.models.uploaded_image_path)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("uploader", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="uploaded_images", to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
