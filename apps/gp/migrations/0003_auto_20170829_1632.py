# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-08-29 16:32
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gp', '0002_auto_20170828_1513'),
    ]

    operations = [
        migrations.CreateModel(
            name='GearGroup',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=64, verbose_name='name')),
            ],
        ),
        migrations.AddField(
            model_name='gear',
            name='gear_group',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='gear_group', to='gp.GearGroup'),
        ),
    ]