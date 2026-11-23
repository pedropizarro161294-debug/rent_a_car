# Carga los permisos y los 2 perfiles de acceso (Administrador y Empleado).
from django.db import migrations

PERMISOS = [
    ("usuarios.ver", "Ver el listado de usuarios"),
    ("usuarios.alta", "Dar de alta usuarios"),
    ("usuarios.modificar", "Modificar el correo de un usuario"),
    ("usuarios.baja", "Dar de baja usuarios"),
    ("usuarios.restablecer_clave", "Restablecer la clave de un usuario"),
    ("empleados.ver", "Ver el listado de empleados"),
    ("empleados.gestionar", "Alta, modificación y baja de empleados"),
]

PERFILES = {
    "Administrador": ("Acceso total al sistema", [p for p, _ in PERMISOS]),
    "Empleado": ("Solo consulta el listado de empleados", ["empleados.ver"]),
}


def cargar(apps, schema_editor):
    Permiso = apps.get_model("usuarios", "Permiso")
    Perfil = apps.get_model("usuarios", "Perfil")
    PerfilPermiso = apps.get_model("usuarios", "PerfilPermiso")
    for nombre, descripcion in PERMISOS:
        Permiso.objects.create(nombre_permiso=nombre, descripcion=descripcion)
    for nombre, (descripcion, permisos) in PERFILES.items():
        perfil = Perfil.objects.create(nombre_perfil=nombre, descripcion=descripcion)
        for p in permisos:
            PerfilPermiso.objects.create(id_perfil=perfil, id_permiso=Permiso.objects.get(nombre_permiso=p))


def borrar(apps, schema_editor):
    apps.get_model("usuarios", "Perfil").objects.all().delete()
    apps.get_model("usuarios", "Permiso").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [("usuarios", "0001_initial")]
    operations = [migrations.RunPython(cargar, borrar)]
