# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2016-12-30 15:58
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gp', '0017_auto_20161226_1636'),
    ]

    operations = [
        migrations.AddField(
            model_name='connector',
            name='icon',
            field=models.ImageField(default=None, null=True, upload_to='media/connector/icon', verbose_name='icon'),
        ),
        migrations.AlterField(
            model_name='connector',
            name='css_class',
            field=models.CharField(blank=True, max_length=40, verbose_name='css class'),
        ),
    ]
