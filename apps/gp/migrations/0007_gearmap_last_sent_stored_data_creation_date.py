# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-09-27 14:45
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gp', '0006_auto_20160920_1538'),
    ]

    operations = [
        migrations.AddField(
            model_name='gearmap',
            name='last_sent_stored_data_creation_date',
            field=models.DateTimeField(default=None, null=True, verbose_name='last sent storeddata creation date'),
        ),
    ]
