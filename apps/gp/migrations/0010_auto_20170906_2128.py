# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-09-06 21:28
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gp', '0009_auto_20170906_2126'),
    ]

    operations = [
        migrations.AlterField(
            model_name='count',
            name='specifications',
            field=models.CharField(max_length=10000, verbose_name='specifications'),
        ),
    ]
