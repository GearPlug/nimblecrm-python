# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2016-11-23 21:57
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gp', '0014_gearmap_last_source_update'),
    ]

    operations = [
        migrations.AlterField(
            model_name='storeddata',
            name='object_id',
            field=models.CharField(max_length=50, null=True, verbose_name='object_id'),
        ),
    ]