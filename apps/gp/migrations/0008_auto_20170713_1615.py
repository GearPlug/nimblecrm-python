# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-07-13 16:15
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gp', '0007_auto_20170706_1606'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gear',
            name='source',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='gear_source', to='gp.Plug'),
        ),
        migrations.AlterField(
            model_name='gear',
            name='target',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='gear_target', to='gp.Plug'),
        ),
        migrations.AlterField(
            model_name='plugactionspecification',
            name='plug',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='plug_action_specification', to='gp.Plug'),
        ),
    ]