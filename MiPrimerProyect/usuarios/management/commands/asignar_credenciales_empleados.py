from django.core.management.base import BaseCommand
from django.db.models import Q

from miprimerapp.models import Empleado
from usuarios.models import Perfil
from usuarios.seguridad import generar_clave_temporal


class Command(BaseCommand):
    help = "Asigna usuario y clave temporal a empleados que aún no tienen cuenta."

    def add_arguments(self, parser):
        parser.add_argument(
            "--perfil",
            default="Empleado",
            help="Nombre del perfil de acceso para empleados sin perfil.",
        )

    def handle(self, *args, **options):
        perfil = Perfil.objects.filter(nombre_perfil=options["perfil"]).first()
        if perfil is None:
            self.stderr.write(f'No existe el perfil "{options["perfil"]}".')
            return

        empleados = Empleado.objects.filter(
            Q(nombre_usuario__isnull=True)
            | Q(nombre_usuario="")
            | Q(clave__isnull=True)
            | Q(clave="")
        ).order_by("apellido", "nombre")

        actualizados = []
        for empleado in empleados:
            necesita_usuario = not empleado.nombre_usuario
            necesita_clave = not empleado.clave

            if empleado.id_perfil_id is None:
                empleado.id_perfil = perfil

            if necesita_usuario:
                empleado.nombre_usuario = None

            clave_temporal = None
            if necesita_clave:
                clave_temporal = generar_clave_temporal()
                empleado.set_clave(clave_temporal, debe_cambiar=True)
            empleado.save()

            actualizados.append((empleado, clave_temporal))

        self.stdout.write(
            self.style.SUCCESS(
                f"Se actualizaron {len(actualizados)} empleado(s). "
                "Las cuentas nuevas o sin clave deben cambiarla en el próximo ingreso."
            )
        )
        for empleado, clave_temporal in actualizados:
            if clave_temporal:
                self.stdout.write(
                    f"{empleado.dni} | {empleado.nombre_usuario} | {clave_temporal}"
                )
            else:
                self.stdout.write(
                    f"{empleado.dni} | {empleado.nombre_usuario} | (conserva clave)"
                )
