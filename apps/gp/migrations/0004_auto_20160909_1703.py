# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-09-09 17:03
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gp', '0003_sugarcrmconnection'),
    ]

    operations = [
        migrations.AlterField(
            model_name='facebookconnection',
            name='name',
            field=models.CharField(max_length=200, verbose_name='name'),
        ),
        migrations.AlterField(
            model_name='mysqlconnection',
            name='connection_user',
            field=models.CharField(max_length=60, verbose_name='user'),
        ),
        migrations.AlterField(
            model_name='mysqlconnection',
            name='database',
            field=models.CharField(max_length=200, verbose_name='database'),
        ),
        migrations.AlterField(
            model_name='mysqlconnection',
            name='host',
            field=models.CharField(max_length=200, verbose_name='host'),
        ),
        migrations.AlterField(
            model_name='mysqlconnection',
            name='name',
            field=models.CharField(max_length=200, verbose_name='name'),
        ),
        migrations.AlterField(
            model_name='mysqlconnection',
            name='port',
            field=models.CharField(max_length=7, verbose_name='port'),
        ),
        migrations.AlterField(
            model_name='mysqlconnection',
            name='table',
            field=models.CharField(max_length=200, verbose_name='table'),
        ),
        migrations.AlterField(
            model_name='sugarcrmconnection',
            name='connection_user',
            field=models.CharField(max_length=60, verbose_name='user'),
        ),
        migrations.AlterField(
            model_name='sugarcrmconnection',
            name='name',
            field=models.CharField(max_length=200, verbose_name='name'),
        ),
        migrations.AlterField(
            model_name='sugarcrmconnection',
            name='url',
            field=models.CharField(max_length=200, verbose_name='url'),
        ),
    ]
