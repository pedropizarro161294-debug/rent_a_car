from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("miprimerapp", "0002_unificar_cuentas_en_empleados"),
        ("usuarios", "0002_cargar_perfiles_y_permisos"),
    ]

    operations = [
        migrations.DeleteModel(name="Usuario"),
    ]
