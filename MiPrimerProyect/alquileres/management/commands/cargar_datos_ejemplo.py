# Uso: python manage.py cargar_datos_ejemplo
# Carga 3 categorías y 3 vehículos con tarifas reales de referencia (Perfil Rent a Car).
# Se puede ejecutar varias veces: si ya existen, actualiza sus datos sin duplicarlos.
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from miprimerapp.models import CategoriaVehiculo, Vehiculo

CATEGORIAS = [
    {
        "nombre_categoria": "Económico",
        "tamanio": "Chico",
        "tarifa": Decimal("50000"),
        "precio": Decimal("350000"),
        "equipamiento": "Aire acondicionado, ABS, airbags, km ilimitado",
    },
    {
        "nombre_categoria": "Sedán",
        "tamanio": "Mediano",
        "tarifa": Decimal("68700"),
        "precio": Decimal("480900"),
        "equipamiento": "Aire acondicionado, ABS, airbags, baúl, km ilimitado",
    },
    {
        "nombre_categoria": "Camioneta 4x4",
        "tamanio": "Grande",
        "tarifa": Decimal("170000"),
        "precio": Decimal("1190000"),
        "equipamiento": "4x4, caja automática, dirección hidráulica, aire acondicionado, ABS, airbags, km ilimitado",
    },
]

# Patentes de ejemplo (inventadas).
VEHICULOS = [
    {"patente": "AE123FG", "marca": "Chevrolet", "modelo": "Onix 1.4 manual", "categoria": "Económico"},
    {"patente": "AF456HJ", "marca": "Renault", "modelo": "Logan 1.6 manual", "categoria": "Sedán"},
    {"patente": "AG789KL", "marca": "Toyota", "modelo": "Hilux 2.8 automática 4x4", "categoria": "Camioneta 4x4"},
]


class Command(BaseCommand):
    help = "Carga categorías y vehículos de ejemplo con tarifas reales de referencia."

    @transaction.atomic
    def handle(self, *args, **options):
        categorias = {}
        for datos in CATEGORIAS:
            datos = dict(datos)
            nombre = datos.pop("nombre_categoria")
            categoria, creada = CategoriaVehiculo.objects.update_or_create(
                nombre_categoria=nombre, defaults={**datos, "estado": "ACTIVO"}
            )
            categorias[nombre] = categoria
            self.stdout.write(f"{'Creada' if creada else 'Actualizada'} categoría {nombre} (${categoria.tarifa}/día)")
        for datos in VEHICULOS:
            datos = dict(datos)
            categoria = categorias[datos.pop("categoria")]
            patente = datos.pop("patente")
            vehiculo, creado = Vehiculo.objects.get_or_create(
                patente=patente, defaults={**datos, "id_categoria": categoria}
            )
            if not creado:
                # No toca el estado operativo: si está alquilado, sigue alquilado.
                vehiculo.marca, vehiculo.modelo, vehiculo.id_categoria = datos["marca"], datos["modelo"], categoria
                vehiculo.save(update_fields=["marca", "modelo", "id_categoria"])
            self.stdout.write(f"{'Creado' if creado else 'Actualizado'} vehículo {patente} - {vehiculo.marca} {vehiculo.modelo}")
        self.stdout.write(self.style.SUCCESS("Datos de ejemplo cargados."))
