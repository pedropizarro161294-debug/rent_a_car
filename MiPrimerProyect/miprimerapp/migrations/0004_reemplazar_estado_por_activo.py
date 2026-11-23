from django.db import migrations, models


def migrar_estado(apps, schema_editor):
    Empleado = apps.get_model("miprimerapp", "Empleado")
    Empleado.objects.filter(estado="ACTIVO").update(activo="SI")
    Empleado.objects.filter(estado="INACTIVO").update(activo="NO")


def restaurar_estado(apps, schema_editor):
    Empleado = apps.get_model("miprimerapp", "Empleado")
    Empleado.objects.filter(activo="SI").update(estado="ACTIVO")
    Empleado.objects.filter(activo="NO").update(estado="INACTIVO")


class Migration(migrations.Migration):

    dependencies = [
        ("miprimerapp", "0003_quitar_campos_laborales_empleado"),
    ]

    operations = [
        migrations.AddField(
            model_name="empleado",
            name="activo",
            field=models.CharField(
                choices=[("SI", "Sí"), ("NO", "No")],
                db_column="ACTIVO",
                default="SI",
                max_length=2,
            ),
        ),
        migrations.RunPython(migrar_estado, restaurar_estado),
        migrations.RemoveField(
            model_name="empleado",
            name="estado",
        ),
    ]
