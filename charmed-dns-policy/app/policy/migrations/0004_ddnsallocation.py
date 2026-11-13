# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

from django.db import migrations, models
import django.utils.timezone

DDNS_ALLOCATION_PERMISSIONS = ["view_ddnsallocation"]


def grant_ddns_allocation_permissions(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    reviewer_group, _ = Group.objects.get_or_create(name="Reviewers")
    content_type, _ = ContentType.objects.get_or_create(
        app_label="policy", model="ddnsallocation"
    )
    for codename in DDNS_ALLOCATION_PERMISSIONS:
        permission, _ = Permission.objects.get_or_create(
            codename=codename,
            content_type=content_type,
            defaults={"name": f"Can {codename.replace('_', ' ')}"},
        )
        reviewer_group.permissions.add(permission)


def revoke_ddns_allocation_permissions(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    reviewer_group = Group.objects.filter(name="Reviewers").first()
    if reviewer_group is None:
        return
    reviewer_group.permissions.remove(
        *Permission.objects.filter(
            content_type__app_label="policy", codename__in=DDNS_ALLOCATION_PERMISSIONS
        )
    )


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("policy", "0003_create_charm_user"),
    ]

    operations = [
        migrations.CreateModel(
            name="DdnsAllocation",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("instance", models.UUIDField()),
                ("requirer_id", models.CharField(max_length=255)),
                ("domain", models.CharField(max_length=253, unique=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
            ],
        ),
        migrations.RunPython(
            grant_ddns_allocation_permissions, revoke_ddns_allocation_permissions
        ),
    ]
