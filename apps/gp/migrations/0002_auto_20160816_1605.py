# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-08-16 16:05
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gp', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='connection',
            name='connector',
            field=models.ForeignKey(default=2, on_delete=django.db.models.deletion.CASCADE, to='gp.Connector'),
        ),
        migrations.AlterField(
            model_name='facebookconnection',
            name='connection',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='connection_facebook', to='gp.Connection'),
        ),
        migrations.AlterField(
            model_name='mysqlconnection',
            name='connection',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='connection_mysql', to='gp.Connection'),
        ),
        migrations.AlterField(
            model_name='mysqlconnection',
            name='connection_password',
            field=models.CharField(max_length=40, verbose_name='password'),
        ),
        migrations.AlterField(
            model_name='mysqlconnection',
            name='database',
            field=models.CharField(max_length=40, verbose_name='database'),
        ),
    ]
