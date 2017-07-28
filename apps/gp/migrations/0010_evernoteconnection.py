# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-07-25 20:51
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gp', '0009_auto_20170725_2024'),
    ]

    operations = [
        migrations.CreateModel(
            name='EvernoteConnection',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='name')),
                ('token', models.CharField(max_length=100, verbose_name='token')),
                ('connection', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='connection_evernote', to='gp.Connection')),
            ],
        ),
    ]
