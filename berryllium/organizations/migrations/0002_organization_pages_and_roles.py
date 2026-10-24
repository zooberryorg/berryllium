import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.utils.text import slugify

import berryllium.organizations.models
import berryllium.shared.links


def fill_in(apps, schema_editor):
    Organization = apps.get_model("organizations", "Organization")
    Membership = apps.get_model("organizations", "OrganizationMembership")
    names, slugs = set(), set()
    for org in Organization.objects.order_by("pk"):
        name = (org.name or "Organization").strip()[:90] or "Organization"
        candidate, n = name, 2
        while candidate.lower() in names:
            candidate, n = f"{name} ({n})", n + 1
        names.add(candidate.lower())
        base = slugify(candidate)[:100] or "organization"
        slug, n = base, 2
        while slug in slugs:
            slug, n = f"{base}-{n}", n + 1
        slugs.add(slug)
        Organization.objects.filter(pk=org.pk).update(name=candidate, slug=slug, description=org.description or "")
    Membership.objects.exclude(role__in=["owner", "co_owner", "member"]).update(role="member")
    for org in Organization.objects.all():
        memberships = Membership.objects.filter(organization=org).order_by("joined_at", "pk")
        if memberships.exists() and not memberships.filter(role="owner").exists():
            memberships.filter(pk=memberships.first().pk).update(role="owner")


class Migration(migrations.Migration):
    dependencies = [
        ("organizations", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # organization page
        migrations.AddField(model_name="organization", name="slug", field=models.SlugField(max_length=110, null=True)),
        migrations.AddField(model_name="organization", name="tagline", field=models.CharField(blank=True, max_length=160)),
        migrations.AddField(model_name="organization", name="logo", field=models.ImageField(blank=True, upload_to=berryllium.organizations.models.org_logo_path)),
        migrations.AddField(model_name="organization", name="banner", field=models.ImageField(blank=True, upload_to=berryllium.organizations.models.org_banner_path)),
        migrations.AddField(model_name="organization", name="accepts_requests", field=models.BooleanField(default=True)),
        migrations.AddField(
            model_name="organization",
            name="created_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL),
        ),
        # memberships
        migrations.AddField(model_name="organizationmembership", name="title", field=models.CharField(blank=True, max_length=80)),
        migrations.AddField(model_name="organizationmembership", name="can_publish", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="organizationmembership", name="can_use_inbox", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="organizationmembership", name="can_edit_profile", field=models.BooleanField(default=False)),
        migrations.RunPython(fill_in, migrations.RunPython.noop),
        migrations.AlterField(model_name="organization", name="name", field=models.CharField(max_length=100, unique=True)),
        migrations.AlterField(model_name="organization", name="slug", field=models.SlugField(max_length=110, unique=True)),
        migrations.AlterField(model_name="organization", name="description", field=models.TextField(blank=True, default="")),
        migrations.AlterModelOptions(name="organization", options={"ordering": ["name"]}),
        migrations.AlterField(
            model_name="organizationmembership",
            name="role",
            field=models.CharField(choices=[("owner", "Owner"), ("co_owner", "Co-owner"), ("member", "Member")], default="member", max_length=50),
        ),
        migrations.AlterField(
            model_name="organizationmembership",
            name="user",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="organization_memberships", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name="organizationmembership",
            name="organization",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="memberships", to="organizations.organization"),
        ),
        migrations.AlterModelOptions(name="organizationmembership", options={"ordering": ["joined_at"]}),
        migrations.AddConstraint(
            model_name="organizationmembership",
            constraint=models.UniqueConstraint(fields=("user", "organization"), name="org_one_membership_each"),
        ),
        # links, invitations and requests
        migrations.CreateModel(
            name="OrganizationLink",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=berryllium.shared.links.LINK_PRESET_CHOICES, default=berryllium.shared.links.DEFAULT_LINK_PRESET, max_length=30)),
                ("url", models.URLField(max_length=500)),
                ("label", models.CharField(blank=True, help_text="Optional; defaults to the preset name.", max_length=100)),
                ("order", models.PositiveIntegerField(default=0)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="links", to="organizations.organization")),
            ],
            options={"ordering": ["order", "id"], "abstract": False},
        ),
        migrations.CreateModel(
            name="OrganizationRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("invite", "Invitation"), ("request", "Request to join")], max_length=10)),
                ("message", models.CharField(blank=True, max_length=300)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("member", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="organization_requests", to=settings.AUTH_USER_MODEL)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="requests", to="organizations.organization")),
            ],
            options={
                "ordering": ["-created_at"],
                "constraints": [models.UniqueConstraint(fields=("organization", "member"), name="org_one_open_request_each")],
            },
        ),
    ]
