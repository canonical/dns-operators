# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

import django.db.models.deletion
import django.utils.timezone
import policy.domains
from django.db import migrations, models

RULE_PERMISSIONS = ["view_rule", "add_rule", "change_rule", "delete_rule"]


def grant_rule_permissions(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    reviewer_group, _ = Group.objects.get_or_create(name="Reviewers")
    rule_content_type, _ = ContentType.objects.get_or_create(app_label="policy", model="rule")
    for codename in RULE_PERMISSIONS:
        permission, _ = Permission.objects.get_or_create(
            codename=codename,
            content_type=rule_content_type,
            defaults={"name": f"Can {codename.replace('_', ' ')}"},
        )
        reviewer_group.permissions.add(permission)


def revoke_rule_permissions(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    reviewer_group = Group.objects.filter(name="Reviewers").first()
    if reviewer_group is None:
        return
    reviewer_group.permissions.remove(
        *Permission.objects.filter(
            content_type__app_label="policy", codename__in=RULE_PERMISSIONS
        )
    )


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('contenttypes', '0002_remove_content_type_name'),
        ('policy', '0004_ddnsallocation'),
    ]

    operations = [
        migrations.CreateModel(
            name='Rule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('kind', models.CharField(choices=[('acme_challenge', 'ACME challenge TXT record of a domain owned by the same requirer')], max_length=50)),
                ('domain', models.CharField(help_text='The rule only applies to the records of this domain and its subdomains.', max_length=253, validators=[policy.domains.validate_domain])),
                ('action', models.CharField(choices=[('approved', 'Approve'), ('denied', 'Deny')], default='approved', max_length=50)),
                ('enabled', models.BooleanField(default=True)),
                ('priority', models.IntegerField(default=0, help_text='Rules with a lower priority are evaluated first.')),
                ('description', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('last_modified_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['priority', 'id'],
            },
        ),
        migrations.AddField(
            model_name='recordrequest',
            name='rule',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='record_requests', to='policy.rule'),
        ),
        migrations.AddField(
            model_name='recordrequest',
            name='instance',
            field=models.UUIDField(blank=True, null=True),
        ),
        migrations.RunPython(grant_rule_permissions, revoke_rule_permissions),
    ]
