# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-06-09 13:50
from __future__ import unicode_literals

import apps.gp.model_fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gp', '0001_squashed_0027_auto_20170517_1933'),
    ]

    operations = [
        migrations.CreateModel(
            name='InstagramConnection',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='name')),
                ('token', models.CharField(max_length=300, verbose_name='token')),
                ('connection', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='connection_instagram', to='gp.Connection')),
            ],
        ),
        migrations.CreateModel(
            name='SMSConnection',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='name')),
                ('connection_user', models.CharField(max_length=60, verbose_name='user')),
                ('connection_password', models.CharField(max_length=40, verbose_name='password')),
                ('connection', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='connection_sms', to='gp.Connection')),
            ],
        ),
        migrations.CreateModel(
            name='WunderListConnection',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='name')),
                ('token', models.CharField(max_length=300, verbose_name='token')),
                ('connection', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='connection_wunderlist', to='gp.Connection')),
            ],
        ),
        migrations.CreateModel(
            name='YouTubeConnection',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='name')),
                ('credentials_json', apps.gp.model_fields.JSONField(blank=True, null=True)),
                ('connection', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='connection_youtube', to='gp.Connection')),
            ],
        ),
        migrations.CreateModel(
            name='ZohoCRMConnection',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.CharField(max_length=300, verbose_name='token')),
                ('name', models.CharField(max_length=200, verbose_name='name')),
                ('connection', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='connection_zohocrm', to='gp.Connection')),
            ],
        ),
    ]
