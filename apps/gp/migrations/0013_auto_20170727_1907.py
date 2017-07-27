# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-07-27 19:07
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gp', '0012_asanaconnection_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='asanaconnection',
            name='token_expiration_timestamp',
            field=models.CharField(default='', max_length=300, verbose_name='token expiration timestamp'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='asanaconnection',
            name='refresh_token',
            field=models.CharField(max_length=300, verbose_name='refresh token'),
        ),
    ]
