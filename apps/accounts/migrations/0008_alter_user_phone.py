# Generated by Django 4.2 on 2025-03-29 21:39

from django.db import migrations
import phonenumber_field.modelfields


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_user_company_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='phone',
            field=phonenumber_field.modelfields.PhoneNumberField(blank=True, max_length=128, null=True, region='BY', unique=True, verbose_name='Номер телефона'),
        ),
    ]
