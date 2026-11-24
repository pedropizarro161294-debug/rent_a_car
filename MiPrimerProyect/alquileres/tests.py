from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from miprimerapp.models import CategoriaVehiculo, Cliente, ContratoAlquiler, DetalleContrato, Vehiculo
from usuarios.tests import crear_usuario, ingresar

from . import servicios


class BaseAlquiler(TestCase):
    def setUp(self):
        self.admin = crear_usuario(20111222, "Admin", "Test", "Administrador")
        self.empleado = crear_usuario(30111222, "Empleado", "Test", "Empleado")
        self.categoria = CategoriaVehiculo.objects.create(
            nombre_categoria="SUV", tarifa=Decimal("10000"), tamanio="Grande", precio=Decimal("0")
        )
        self.v1 = Vehiculo.objects.create(patente="AB123CD", marca="Toyota", modelo="Hilux", id_categoria=self.categoria)
        self.v2 = Vehiculo.objects.create(patente="AC456EF", marca="Ford", modelo="Ranger", id_categoria=self.categoria)
        self.cliente = Cliente.objects.create(dni="35111222", nombre="Ana", apellido="López")
        self.hoy = timezone.localdate()

    def datos(self, **extra):
        datos = {
            "id_cliente": self.cliente.pk,
            "fecha_inicio": self.hoy.isoformat(),
            "fecha_fin": (self.hoy + timedelta(days=3)).isoformat(),
            "porcentaje_descuento": "10",
            "vehiculos": [self.v1.pk, self.v2.pk],
            "condiciones": "",
        }
        datos.update(extra)
        return datos


class CalculosTests(TestCase):
    def test_calculo_de_importes(self):
        r = servicios.calcular_importes([Decimal("10000"), Decimal("5000")], 3, Decimal("10"))
        self.assertEqual(r["renglones"], [Decimal("30000.00"), Decimal("15000.00")])
        self.assertEqual(r["subtotal"], Decimal("45000.00"))
        self.assertEqual(r["importe_descuento"], Decimal("4500.00"))
        self.assertEqual(r["importe_iva"], Decimal("8505.00"))
        self.assertEqual(r["monto_total"], Decimal("49005.00"))

    def test_mismo_dia_cuenta_un_dia(self):
        hoy = timezone.localdate()
        self.assertEqual(servicios.calcular_dias(hoy, hoy), 1)


class RegistrarAlquilerTests(BaseAlquiler):
    def test_registra_cabecera_detalle_y_actualiza_vehiculos(self):
        ingresar(self.client, self.empleado.nombre_usuario)
        respuesta = self.client.post(reverse("alquileres:registrar"), self.datos())
        contrato = ContratoAlquiler.objects.get()
        self.assertRedirects(respuesta, reverse("alquileres:detalle", args=[contrato.pk]))
        self.assertEqual(contrato.numero_contrato, f"A-{contrato.pk:08d}")
        self.assertEqual(contrato.id_empleado, self.empleado)
        self.assertEqual(contrato.estado, "CONFIRMADO")
        self.assertEqual(contrato.cantidad_dias, 3)
        self.assertEqual(contrato.monto_total, Decimal("65340.00"))  # 60000 - 10% + 21% IVA
        self.assertEqual(contrato.detalles.count(), 2)
        self.v1.refresh_from_db()
        self.assertEqual(self.v1.estado_operativo, "ALQUILADO")

    def test_validaciones(self):
        ingresar(self.client, self.admin.nombre_usuario)
        ayer = (self.hoy - timedelta(days=1)).isoformat()
        r = self.client.post(reverse("alquileres:registrar"), self.datos(fecha_inicio=ayer, vehiculos=[], porcentaje_descuento="80"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "no puede ser anterior a hoy")
        self.assertContains(r, "Elegí al menos un vehículo")
        self.assertFalse(ContratoAlquiler.objects.exists())

    def test_no_permite_vehiculo_alquilado(self):
        ingresar(self.client, self.admin.nombre_usuario)
        self.v1.estado_operativo = "ALQUILADO"
        self.v1.save()
        r = self.client.post(reverse("alquileres:registrar"), self.datos())
        self.assertEqual(r.status_code, 200)
        self.assertFalse(ContratoAlquiler.objects.exists())

    def test_transaccion_revierte_todo_si_falla(self):
        with mock.patch.object(DetalleContrato.objects, "create", side_effect=RuntimeError("falla")):
            with self.assertRaises(RuntimeError):
                servicios.registrar_alquiler(
                    cliente=self.cliente,
                    vehiculos=[self.v1],
                    fecha_inicio=self.hoy,
                    fecha_fin=self.hoy + timedelta(days=1),
                    porcentaje_descuento=Decimal("0"),
                    condiciones="",
                    usuario=self.admin,
                )
        self.assertFalse(ContratoAlquiler.objects.exists())
        self.v1.refresh_from_db()
        self.assertEqual(self.v1.estado_operativo, "DISPONIBLE")


class AnulacionYPermisosTests(BaseAlquiler):
    def setUp(self):
        super().setUp()
        self.contrato = servicios.registrar_alquiler(
            cliente=self.cliente,
            vehiculos=[self.v1],
            fecha_inicio=self.hoy,
            fecha_fin=self.hoy + timedelta(days=2),
            porcentaje_descuento=Decimal("0"),
            condiciones="",
            usuario=self.empleado,
        )

    def test_empleado_no_puede_anular(self):
        ingresar(self.client, self.empleado.nombre_usuario)
        r = self.client.post(reverse("alquileres:anular", args=[self.contrato.pk]), {"motivo": "Cliente desistió"})
        self.assertRedirects(r, reverse("inicio"))
        self.contrato.refresh_from_db()
        self.assertEqual(self.contrato.estado, "CONFIRMADO")

    def test_admin_anula_y_revierte(self):
        ingresar(self.client, self.admin.nombre_usuario)
        self.client.post(reverse("alquileres:anular", args=[self.contrato.pk]), {"motivo": "Cliente desistió"})
        self.contrato.refresh_from_db()
        self.assertEqual(self.contrato.estado, "ANULADO")
        self.assertEqual(self.contrato.id_empleado_anulacion, self.admin)
        self.assertEqual(self.contrato.motivo_anulacion, "Cliente desistió")
        self.assertIsNotNone(self.contrato.fecha_anulacion)
        self.v1.refresh_from_db()
        self.assertEqual(self.v1.estado_operativo, "DISPONIBLE")
        self.assertTrue(ContratoAlquiler.objects.filter(pk=self.contrato.pk).exists())  # no se borra

    def test_finalizar_libera_vehiculos(self):
        ingresar(self.client, self.empleado.nombre_usuario)
        self.client.post(reverse("alquileres:finalizar", args=[self.contrato.pk]))
        self.contrato.refresh_from_db()
        self.assertEqual(self.contrato.estado, "FINALIZADO")
        self.v1.refresh_from_db()
        self.assertEqual(self.v1.estado_operativo, "DISPONIBLE")

    def test_consulta_filtra_y_comprobante(self):
        ingresar(self.client, self.empleado.nombre_usuario)
        r = self.client.get(reverse("alquileres:consulta"), {"estado": "CONFIRMADO", "cliente": self.cliente.pk})
        self.assertContains(r, self.contrato.numero_contrato)
        r = self.client.get(reverse("alquileres:consulta"), {"estado": "ANULADO"})
        self.assertNotContains(r, self.contrato.numero_contrato)
        r = self.client.get(reverse("alquileres:comprobante", args=[self.contrato.pk]))
        self.assertContains(r, "Comprobante de alquiler")
        self.assertContains(r, "AB123CD")

    def test_empleado_no_gestiona_vehiculos(self):
        ingresar(self.client, self.empleado.nombre_usuario)
        r = self.client.get(reverse("alquileres:vehiculos"))
        self.assertRedirects(r, reverse("inicio"))


class AbmTests(BaseAlquiler):
    def test_alta_cliente_y_baja_logica(self):
        ingresar(self.client, self.admin.nombre_usuario)
        self.client.post(reverse("alquileres:cliente_alta"), {"dni": "40111222", "apellido": "Ruiz", "nombre": "Juan", "telefono": "11 5555-1234"})
        cliente = Cliente.objects.get(dni="40111222")
        self.assertEqual(cliente.telefonos.get().telefono, "11 5555-1234")
        self.client.post(reverse("alquileres:cliente_estado", args=[cliente.pk]))
        cliente.refresh_from_db()
        self.assertEqual(cliente.estado, "INACTIVO")

    def test_no_baja_vehiculo_alquilado(self):
        ingresar(self.client, self.admin.nombre_usuario)
        self.v1.estado_operativo = "ALQUILADO"
        self.v1.save()
        self.client.post(reverse("alquileres:vehiculo_estado", args=[self.v1.pk]))
        self.v1.refresh_from_db()
        self.assertEqual(self.v1.estado, "ACTIVO")

    def test_patente_se_normaliza(self):
        ingresar(self.client, self.admin.nombre_usuario)
        self.client.post(reverse("alquileres:vehiculo_alta"), {"patente": "ad 789 gh", "marca": "VW", "modelo": "Amarok", "id_categoria": self.categoria.pk, "estado_operativo": "DISPONIBLE"})
        self.assertTrue(Vehiculo.objects.filter(patente="AD789GH").exists())


class DatosEjemploTests(TestCase):
    def test_carga_y_se_puede_repetir(self):
        from django.core.management import call_command
        from io import StringIO

        call_command("cargar_datos_ejemplo", stdout=StringIO())
        call_command("cargar_datos_ejemplo", stdout=StringIO())
        self.assertEqual(CategoriaVehiculo.objects.get(nombre_categoria="Camioneta 4x4").tarifa, Decimal("170000"))
        self.assertEqual(Vehiculo.objects.filter(patente__in=["AE123FG", "AF456HJ", "AG789KL"]).count(), 3)
        self.assertEqual(Vehiculo.objects.get(patente="AF456HJ").id_categoria.nombre_categoria, "Sedán")
