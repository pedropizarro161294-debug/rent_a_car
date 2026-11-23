from django.db import migrations, models
import django.db.models.deletion


def unificar_cuentas(apps, schema_editor):
    Usuario = apps.get_model("usuarios", "Usuario")
    Empleado = apps.get_model("miprimerapp", "Empleado")
    empleados_por_dni = {
        str(empleado.dni): empleado
        for empleado in Empleado.objects.all().iterator()
    }

    for usuario in Usuario.objects.all().iterator():
        dni = str(usuario.dni)
        empleado = empleados_por_dni.get(dni)
        if empleado is None and len(dni) < 8:
            empleado = empleados_por_dni.get(dni.zfill(8))
        if empleado is None:
            empleado = Empleado.objects.create(
                dni=dni,
                apellido=usuario.apellido,
                nombre=usuario.nombre,
                cargo=usuario.id_perfil.nombre_perfil,
                fecha_alta=usuario.fecha_ultima_modificacion.date(),
            )
            empleados_por_dni[dni] = empleado

        Empleado.objects.filter(pk=empleado.pk).update(
            correo=usuario.correo,
            nombre_usuario=usuario.nombre_usuario,
            clave=usuario.clave,
            estado="ACTIVO" if usuario.activo else "INACTIVO",
            debe_cambiar_clave=usuario.debe_cambiar_clave,
            fecha_ultima_modificacion=usuario.fecha_ultima_modificacion,
            fecha_baja=usuario.fecha_baja,
            id_perfil_id=usuario.id_perfil_id,
        )


def restaurar_cuentas(apps, schema_editor):
    Empleado = apps.get_model("miprimerapp", "Empleado")
    Usuario = apps.get_model("usuarios", "Usuario")

    for empleado in Empleado.objects.filter(nombre_usuario__isnull=False).iterator():
        usuario = Usuario.objects.create(
            dni=int(empleado.dni),
            apellido=empleado.apellido,
            nombre=empleado.nombre,
            correo=empleado.correo,
            nombre_usuario=empleado.nombre_usuario,
            clave=empleado.clave,
            activo=empleado.estado == "ACTIVO",
            debe_cambiar_clave=empleado.debe_cambiar_clave,
            fecha_baja=empleado.fecha_baja,
            id_perfil_id=empleado.id_perfil_id,
        )
        Usuario.objects.filter(pk=usuario.pk).update(
            fecha_ultima_modificacion=empleado.fecha_ultima_modificacion
        )


class Migration(migrations.Migration):

    dependencies = [
        ("miprimerapp", "0001_initial"),
        ("usuarios", "0002_cargar_perfiles_y_permisos"),
    ]

    operations = [
        migrations.AddField(
            model_name="empleado",
            name="correo",
            field=models.EmailField(
                blank=True,
                db_column="CORREO",
                max_length=100,
                null=True,
                unique=True,
            ),
        ),
        migrations.AddField(
            model_name="empleado",
            name="nombre_usuario",
            field=models.CharField(
                blank=True,
                db_column="NOMBRE_USUARIO",
                editable=False,
                max_length=60,
                null=True,
                unique=True,
            ),
        ),
        migrations.AddField(
            model_name="empleado",
            name="clave",
            field=models.CharField(blank=True, db_column="CLAVE", max_length=128, null=True),
        ),
        migrations.AddField(
            model_name="empleado",
            name="debe_cambiar_clave",
            field=models.BooleanField(db_column="DEBE_CAMBIAR_CLAVE", default=False),
        ),
        migrations.AddField(
            model_name="empleado",
            name="fecha_ultima_modificacion",
            field=models.DateTimeField(
                auto_now=True,
                blank=True,
                db_column="FECHA_ULTIMA_MODIFICACION",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="empleado",
            name="fecha_baja",
            field=models.DateTimeField(blank=True, db_column="FECHA_BAJA", null=True),
        ),
        migrations.AddField(
            model_name="empleado",
            name="id_perfil",
            field=models.ForeignKey(
                blank=True,
                db_column="ID_PERFIL",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="empleados",
                to="usuarios.perfil",
            ),
        ),
        migrations.RunPython(unificar_cuentas, restaurar_cuentas),
        migrations.AlterModelTable(name="empleado", table="empleados"),
    ]
