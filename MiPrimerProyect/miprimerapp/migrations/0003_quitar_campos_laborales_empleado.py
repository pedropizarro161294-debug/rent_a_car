from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("miprimerapp", "0002_unificar_cuentas_en_empleados"),
        ("usuarios", "0003_eliminar_tabla_usuario"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="empleado",
            name="cargo",
        ),
        migrations.RemoveField(
            model_name="empleado",
            name="informacion_laboral",
        ),
        migrations.RemoveField(
            model_name="empleado",
            name="funcion",
        ),
    ]
