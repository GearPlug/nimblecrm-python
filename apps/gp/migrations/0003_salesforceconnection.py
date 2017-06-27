# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2017-06-26 14:26
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gp', '0002_instagramconnection_smsconnection_wunderlistconnection_youtubeconnection_zohocrmconnection'),
    ]

    operations = [
        migrations.CreateModel(
            name='SalesforceConnection',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='name')),
                ('connection_user', models.CharField(max_length=60, verbose_name='user')),
                ('connection_password', models.CharField(max_length=40, verbose_name='password')),
                ('token', models.CharField(max_length=40, verbose_name='token')),
                ('connection', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='connection_salesforce', to='gp.Connection')),
            ],
        ),
    ]
