import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inbox", "0001_initial"),
        ("organizations", "0002_organization_pages_and_roles"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="conversation",
            name="organization",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="conversations",
                to="organizations.organization",
            ),
        ),
        migrations.AddField(
            model_name="conversationmember",
            name="organization",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="conversation_memberships",
                to="organizations.organization",
            ),
        ),
        migrations.AddField(
            model_name="message",
            name="sent_as",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="organizations.organization",
            ),
        ),
        migrations.AlterField(
            model_name="conversationmember",
            name="member",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="conversation_memberships",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
