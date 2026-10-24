from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="notification",
            name="kind",
            field=models.CharField(
                choices=[
                    ("comment", "New comment"),
                    ("reply", "Reply"),
                    ("quote", "Quote"),
                    ("message", "Message"),
                    ("organization", "Organization"),
                ],
                max_length=20,
            ),
        ),
    ]
