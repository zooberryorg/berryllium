from django.db import migrations, models

import berryllium.users.models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0003_member_date_format_member_time_format"),
    ]

    operations = [
        migrations.AddField(
            model_name="member",
            name="avatar",
            field=models.ImageField(blank=True, upload_to=berryllium.users.models.member_avatar_path),
        ),
    ]
