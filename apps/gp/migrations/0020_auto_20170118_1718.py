# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2017-01-18 17:18
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gp', '0019_auto_20170118_1717'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='facebookconnection',
            name='id_form',
        ),
        migrations.RemoveField(
            model_name='facebookconnection',
            name='id_page',
        ),
    ]
