# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2017-07-07 11:32
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gp', '0003_salesforceconnection'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='salesforceconnection',
            name='connection_password',
        ),
        migrations.RemoveField(
            model_name='salesforceconnection',
            name='connection_user',
        ),
        migrations.AlterField(
            model_name='salesforceconnection',
            name='token',
            field=models.CharField(max_length=300, verbose_name='token'),
        ),
    ]
