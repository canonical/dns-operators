# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

import django.db.models.deletion
import django.utils.timezone
import policy.domains
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
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
    ]
