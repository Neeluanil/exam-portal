# Generated by Django 5.1.7 on 2025-04-07 19:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0005_studentexamsubmission_flagged'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentexamsubmission',
            name='is_published',
            field=models.BooleanField(default=False),
        ),
    ]
