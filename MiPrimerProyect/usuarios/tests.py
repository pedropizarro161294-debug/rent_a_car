from datetime import date

from django.test import TestCase
from django.urls import reverse

from miprimerapp.models import Empleado
from .models import Perfil


def crear_usuario(dni, apellido, nombre, perfil, clave="Clave123!", debe_cambiar=False):
    perfil_obj = Perfil.objects.get(nombre_perfil=perfil)
    empleado = Empleado(
        dni=str(dni),
        apellido=apellido,
        nombre=nombre,
        correo=f"{dni}@mail.com",
        fecha_alta=date.today(),
        id_perfil=perfil_obj,
    )
    empleado.set_clave(clave, debe_cambiar)
    empleado.save()
    return empleado


def ingresar(client, nombre_usuario, clave="Clave123!"):
    return client.post(reverse("login"), {"nombre_usuario": nombre_usuario, "clave": clave})


class CuentasEmpleadoTests(TestCase):
    def setUp(self):
        self.admin = crear_usuario(20111222, "Pérez", "Ana María", "Administrador")
        ingresar(self.client, "pereza")

    def test_usuario_automatico(self):
        self.assertEqual(self.admin.nombre_usuario, "pereza")
        self.assertEqual(crear_usuario(30111222, "Perez", "Alberto", "Empleado").nombre_usuario, "pereza2")

    def test_clave_con_hash(self):
        self.assertTrue(self.admin.clave.startswith("pbkdf2_sha256$"))

    def test_alta_de_empleado_crea_cuenta_y_exige_cambio_de_clave(self):
        respuesta = self.client.post(
            reverse("empleados:alta"),
            {
                "dni": "35000111",
                "apellido": "Gómez",
                "nombre": "Juan",
                "correo": "jg@mail.com",
                "fecha_alta": "2025-01-15",
                "id_perfil": Perfil.objects.get(nombre_perfil="Empleado").pk,
            },
        )
        empleado = Empleado.objects.get(dni="35000111")
        self.assertEqual(empleado.nombre_usuario, "gomezj")
        self.assertTrue(empleado.debe_cambiar_clave)
        otro = self.client_class()
        ingresar(otro, "gomezj", respuesta.context["clave"])
        self.assertRedirects(otro.get(reverse("empleados:panel")), reverse("cambiar_clave"))

    def test_modificar_correo_en_el_panel_de_empleados(self):
        empleado = crear_usuario(30000001, "López", "Carla", "Empleado")
        antes = empleado.fecha_ultima_modificacion
        respuesta = self.client.post(
            reverse("empleados:editar", args=[empleado.id_empleado]),
            {
                "correo": "nuevo@mail.com",
                "nombre": "Nombre modificado",
                "dni": "99999999",
                "id_perfil": "",
            },
        )
        self.assertRedirects(respuesta, reverse("empleados:panel"))
        empleado.refresh_from_db()
        self.assertEqual((empleado.correo, empleado.apellido), ("nuevo@mail.com", "López"))
        self.assertGreater(empleado.fecha_ultima_modificacion, antes)

    def test_baja_desactiva_la_cuenta(self):
        empleado = crear_usuario(30000002, "Díaz", "Pedro", "Empleado")
        self.client.post(reverse("empleados:baja", args=[empleado.id_empleado]))
        empleado.refresh_from_db()
        self.assertEqual(empleado.activo, "NO")
        self.assertIsNotNone(empleado.fecha_baja)

    def test_restablecer_clave(self):
        empleado = crear_usuario(30000003, "Ruiz", "Eva", "Empleado")
        respuesta = self.client.post(reverse("restablecer_clave"), {"usuario": empleado.dni})
        empleado.refresh_from_db()
        self.assertTrue(empleado.debe_cambiar_clave)
        self.assertTrue(empleado.verificar_clave(respuesta.context["clave"]))

    def test_perfil_empleado_usa_el_panel_unificado(self):
        crear_usuario(30000004, "Sosa", "Luis", "Empleado")
        cliente = self.client_class()
        ingresar(cliente, "sosal")
        respuesta = cliente.get(reverse("empleados:panel"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotContains(respuesta, "30000004@mail.com")
        self.assertRedirects(cliente.get(reverse("empleados:alta")), reverse("inicio"))
        self.assertEqual(cliente.get("/usuarios/").status_code, 404)
