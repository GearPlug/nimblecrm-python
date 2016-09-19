# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-09-07 21:31
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gp', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gearmap',
            name='last_sent_stored_data',
            field=models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='gear_map', to='gp.StoredData'),
        ),
    ]
