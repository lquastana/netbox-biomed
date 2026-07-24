"""
Equipment.plateau (FK, un seul) → Equipment.plateaux (M2M).

Migration en 3 temps, sans perte : ajout du M2M (related_name temporaire pour
ne pas entrer en collision avec la FK encore présente), copie des
rattachements existants, suppression de la FK, puis bascule du related_name.
"""
from django.db import migrations, models


def copy_plateau_to_m2m(apps, schema_editor):
    Equipment = apps.get_model('netbox_biomed', 'Equipment')
    for equipment in Equipment.objects.exclude(plateau__isnull=True):
        equipment.plateaux.add(equipment.plateau)


def reverse_copy(apps, schema_editor):
    Equipment = apps.get_model('netbox_biomed', 'Equipment')
    for equipment in Equipment.objects.all():
        first = equipment.plateaux.first()
        if first:
            equipment.plateau = first
            equipment.save(update_fields=['plateau'])


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_biomed', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='equipment',
            name='plateaux',
            field=models.ManyToManyField(
                blank=True,
                related_name='equipments_m2m_tmp',
                to='netbox_biomed.plateau',
                verbose_name='Technical platforms',
            ),
        ),
        migrations.RunPython(copy_plateau_to_m2m, reverse_copy),
        migrations.RemoveField(
            model_name='equipment',
            name='plateau',
        ),
        migrations.AlterField(
            model_name='equipment',
            name='plateaux',
            field=models.ManyToManyField(
                blank=True,
                related_name='equipments',
                to='netbox_biomed.plateau',
                verbose_name='Technical platforms',
                help_text='Technical platforms this equipment belongs to (an equipment can serve several)',
            ),
        ),
    ]
