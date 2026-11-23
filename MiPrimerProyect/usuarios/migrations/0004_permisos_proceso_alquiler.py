# Hito 3: permisos del proceso de alquiler y de los ABM que necesita.
# El perfil Empleado puede registrar, consultar, finalizar e imprimir alquileres,
# pero NO puede anularlos (acción restringida por perfil).
from django.db import migrations

PERMISOS = [
    ("clientes.gestionar", "Alta, modificación y baja de clientes"),
    ("vehiculos.gestionar", "Alta, modificación y baja de vehículos y categorías"),
    ("alquileres.registrar", "Registrar un alquiler"),
    ("alquileres.consultar", "Consultar alquileres y ver su detalle"),
    ("alquileres.finalizar", "Finalizar un alquiler (devolución de vehículos)"),
    ("alquileres.anular", "Anular un alquiler"),
    ("alquileres.comprobante", "Emitir el comprobante de un alquiler"),
]

ASIGNACION = {
    "Administrador": [p for p, _ in PERMISOS],
    "Empleado": [
        "clientes.gestionar",
        "alquileres.registrar",
        "alquileres.consultar",
        "alquileres.finalizar",
        "alquileres.comprobante",
    ],
}

DESCRIPCIONES = {
    "Empleado": "Consulta empleados; registra y consulta alquileres (no puede anular)",
}


def cargar(apps, schema_editor):
    Permiso = apps.get_model("usuarios", "Permiso")
    Perfil = apps.get_model("usuarios", "Perfil")
    PerfilPermiso = apps.get_model("usuarios", "PerfilPermiso")
    for nombre, descripcion in PERMISOS:
        Permiso.objects.get_or_create(nombre_permiso=nombre, defaults={"descripcion": descripcion})
    for nombre_perfil, permisos in ASIGNACION.items():
        perfil = Perfil.objects.filter(nombre_perfil=nombre_perfil).first()
        if perfil is None:
            continue
        if nombre_perfil in DESCRIPCIONES:
            perfil.descripcion = DESCRIPCIONES[nombre_perfil]
            perfil.save()
        for nombre in permisos:
            permiso = Permiso.objects.get(nombre_permiso=nombre)
            if not PerfilPermiso.objects.filter(id_perfil=perfil, id_permiso=permiso).exists():
                PerfilPermiso.objects.create(id_perfil=perfil, id_permiso=permiso)


def borrar(apps, schema_editor):
    apps.get_model("usuarios", "Permiso").objects.filter(nombre_permiso__in=[p for p, _ in PERMISOS]).delete()


class Migration(migrations.Migration):
    dependencies = [("usuarios", "0003_eliminar_tabla_usuario")]
    operations = [migrations.RunPython(cargar, borrar)]
