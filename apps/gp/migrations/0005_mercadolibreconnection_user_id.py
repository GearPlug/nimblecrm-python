# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-09-15 16:00
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gp', '0004_historycount'),
    ]

    operations = [
        migrations.AddField(
            model_name='mercadolibreconnection',
            name='user_id',
            field=models.CharField(default=0, max_length=200, verbose_name='user_id'),
            preserve_default=False,
        ),
    ]
