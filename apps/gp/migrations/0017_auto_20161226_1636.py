# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2016-12-26 16:36
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gp', '0016_googlespreadsheetsconnection'),
    ]

    operations = [
        migrations.CreateModel(
            name='PostgreSQLConnection',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='name')),
                ('host', models.CharField(max_length=200, verbose_name='host')),
                ('database', models.CharField(max_length=200, verbose_name='database')),
                ('table', models.CharField(max_length=200, verbose_name='table')),
                ('port', models.CharField(max_length=7, verbose_name='port')),
                ('connection_user', models.CharField(max_length=60, verbose_name='user')),
                ('connection_password', models.CharField(max_length=40, verbose_name='password')),
                ('connection', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='connection_postgresql', to='gp.Connection')),
            ],
        ),
        migrations.AlterField(
            model_name='googlespreadsheetsconnection',
            name='connection',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='connection_googlespreadsheets', to='gp.Connection'),
        ),
    ]