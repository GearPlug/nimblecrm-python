# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-09-14 16:01
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gp', '0003_auto_20170906_1927'),
    ]

    operations = [
        migrations.CreateModel(
            name='HistoryCount',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name_input', models.CharField(max_length=200, verbose_name='name_input')),
                ('datetime', models.DateTimeField(auto_now_add=True)),
                ('user_id', models.CharField(max_length=200, verbose_name='user_id')),
                ('user_name', models.CharField(max_length=200, verbose_name='user_name')),
                ('gear_id', models.CharField(max_length=200, verbose_name='gear_id')),
                ('plug_id_input', models.CharField(max_length=200, verbose_name='plug_id_input')),
                ('action_input', models.CharField(max_length=200, verbose_name='action_input')),
                ('specifications_input', models.CharField(max_length=1000, verbose_name='specifications_input')),
                ('data_input', models.CharField(max_length=2000, verbose_name='data_input')),
                ('object_id', models.CharField(max_length=200, verbose_name='object_id')),
                ('name_output', models.CharField(max_length=200, verbose_name='name_output')),
                ('plug_id_output', models.CharField(max_length=200, verbose_name='plug_id_output')),
                ('action_output', models.CharField(max_length=200, verbose_name='action_output')),
                ('specifications_output', models.CharField(max_length=1000, verbose_name='specifications_output')),
                ('data_output', models.CharField(max_length=2000, verbose_name='data_output')),
            ],
        ),
    ]
