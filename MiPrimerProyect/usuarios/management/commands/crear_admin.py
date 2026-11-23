# Uso: python manage.py crear_admin DNI APELLIDO NOMBRE CORREO
from django.core.management.base import BaseCommand
from django.utils import timezone

from miprimerapp.models import Empleado
from usuarios.models import Perfil
from usuarios.seguridad import generar_clave_temporal


class Command(BaseCommand):
    help = "Crea el primer usuario con perfil Administrador."

    def add_arguments(self, parser):
        for arg in ["dni", "apellido", "nombre", "correo"]:
            parser.add_argument(arg)

    def handle(self, *args, **o):
        clave = generar_clave_temporal()
        perfil = Perfil.objects.get(nombre_perfil="Administrador")
        u = Empleado(
            dni=str(o["dni"]),
            apellido=o["apellido"],
            nombre=o["nombre"],
            correo=o["correo"],
            fecha_alta=timezone.localdate(),
            id_perfil=perfil,
        )
        u.set_clave(clave, debe_cambiar=True)
        u.save()
        self.stdout.write(f"Usuario: {u.nombre_usuario}   Clave temporal: {clave}")
