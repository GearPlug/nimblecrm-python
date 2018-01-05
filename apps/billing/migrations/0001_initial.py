# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2018-01-04 15:42
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
        ),
        migrations.CreateModel(
            name='ServiceFee',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, verbose_name='')),
                ('value', models.DecimalField(decimal_places=4, max_digits=5, verbose_name='recharge amount')),
            ],
        ),
        migrations.CreateModel(
            name='ServiceRecharge',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('recharge_amount', models.DecimalField(decimal_places=4, max_digits=10, verbose_name='recharge amount')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='created')),
                ('expiration_date', models.DateTimeField(verbose_name='expiration date')),
            ],
        ),
        migrations.CreateModel(
            name='ServiceValidity',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user', models.CharField(max_length=12, verbose_name='user')),
                ('total_recharged', models.DecimalField(decimal_places=4, max_digits=11, verbose_name='recharge amount')),
                ('current_balance', models.DecimalField(decimal_places=4, max_digits=10, verbose_name='current balance')),
                ('last_modified', models.DateTimeField(auto_now=True, verbose_name='last modified')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='created')),
                ('current_fee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='service_validity', to='billing.ServiceFee')),
            ],
        ),
        migrations.CreateModel(
            name='ServiceValidityHistory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('operation', models.CharField(choices=[('1', 'Recharge'), ('2', 'Revoke'), ('3', 'Consumed'), ('4', 'Bonus recharge'), ('5', 'Refunded')], max_length=3, verbose_name='operation')),
                ('amount', models.DecimalField(decimal_places=4, max_digits=10, verbose_name='amount')),
                ('service_validity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='service_validity_history', to='billing.ServiceValidity')),
            ],
        ),
        migrations.AddField(
            model_name='servicerecharge',
            name='service_validity',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='service_recharge', to='billing.ServiceValidity'),
        ),
        migrations.AddField(
            model_name='invoice',
            name='service_recharge',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='billing.ServiceRecharge'),
        ),
    ]
