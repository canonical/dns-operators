# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
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
                ("relation_id", models.IntegerField()),
                ("domain", models.CharField(max_length=253, unique=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
            ],
        ),
    ]
