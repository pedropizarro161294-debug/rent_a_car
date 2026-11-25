from datetime import date

from django.test import TestCase
from django.urls import reverse

from .models import Empleado
from usuarios.models import Perfil
from usuarios.tests import crear_usuario, ingresar


class PanelEmpleadosTests(TestCase):
	def setUp(self):
		# Desde el Hito 2 las pantallas piden login: entramos como Administrador.
		crear_usuario(20111222, "Admin", "Test", "Administrador")
		ingresar(self.client, "admint")

	def crear_empleado(self, **datos):
		valores = {
			"nombre": "Ana",
			"apellido": "García",
			"dni": "12345678",
			"fecha_alta": date(2024, 2, 10),
			"activo": "SI",
		}
		valores.update(datos)
		return Empleado.objects.create(**valores)

	def test_panel_busca_y_filtra_por_estado(self):
		activo = self.crear_empleado()
		self.crear_empleado(nombre="Luis", apellido="Pérez", dni="87654321", activo="NO")

		respuesta = self.client.get(reverse("empleados:panel"), {"q": "Ana", "estado": "ACTIVO"})

		self.assertEqual(respuesta.status_code, 200)
		self.assertContains(respuesta, activo.dni)
		self.assertNotContains(respuesta, "87654321")

	def test_panel_muestra_datos_de_acceso_sin_exponer_el_hash(self):
		empleado = crear_usuario(30112233, "Gómez", "Juan", "Empleado")

		respuesta = self.client.get(reverse("empleados:panel"))

		self.assertContains(respuesta, empleado.correo)
		self.assertContains(respuesta, empleado.nombre_usuario)
		self.assertContains(respuesta, "Empleado")
		self.assertNotContains(respuesta, empleado.clave)

	def test_alta_guarda_empleado(self):
		respuesta = self.client.post(
			reverse("empleados:alta"),
			{
				"nombre": "Sofía",
				"apellido": "López",
				"dni": "55443322",
				"fecha_alta": "2025-01-15",
				"correo": "sofia@mail.com",
				"id_perfil": Perfil.objects.get(nombre_perfil="Empleado").pk,
			},
		)

		self.assertEqual(respuesta.status_code, 200)
		empleado = Empleado.objects.get(dni="55443322", activo="SI")
		self.assertEqual(empleado.activo, "SI")
		self.assertEqual(empleado.nombre_usuario, "lopezs")
		self.assertEqual(empleado.correo, "sofia@mail.com")
		self.assertTrue(empleado.debe_cambiar_clave)
		self.assertTrue(empleado.verificar_clave(respuesta.context["clave"]))

	def test_edicion_actualiza_datos(self):
		empleado = self.crear_empleado()
		antes = empleado.fecha_ultima_modificacion

		respuesta = self.client.post(
			reverse("empleados:editar", args=[empleado.id_empleado]),
			{
				"correo": "ana.nueva@mail.com",
				"nombre": "Nombre modificado",
				"dni": "99999999",
				"id_perfil": "",
			},
		)

		self.assertRedirects(respuesta, reverse("empleados:panel"))
		empleado.refresh_from_db()
		self.assertEqual(empleado.correo, "ana.nueva@mail.com")
		self.assertEqual(empleado.nombre, "Ana")
		self.assertEqual(empleado.dni, "12345678")
		self.assertGreater(empleado.fecha_ultima_modificacion, antes)

	def test_baja_pide_confirmacion_y_luego_desactiva(self):
		empleado = self.crear_empleado()
		url = reverse("empleados:baja", args=[empleado.id_empleado])

		confirmacion = self.client.get(url)
		empleado.refresh_from_db()
		self.assertEqual(confirmacion.status_code, 200)
		self.assertContains(confirmacion, "Sí, dar de baja")
		self.assertEqual(empleado.activo, "SI")

		respuesta = self.client.post(url)
		empleado.refresh_from_db()
		self.assertRedirects(respuesta, reverse("empleados:panel"))
		self.assertEqual(empleado.activo, "NO")
		self.assertIsNotNone(empleado.fecha_baja)

	def test_reactivar_pide_confirmacion_y_luego_activa(self):
		empleado = self.crear_empleado()
		empleado.dar_de_baja()
		url = reverse("empleados:reactivar", args=[empleado.id_empleado])

		confirmacion = self.client.get(url)
		empleado.refresh_from_db()
		self.assertContains(confirmacion, "Sí, reactivar")
		self.assertEqual(empleado.activo, "NO")

		self.client.post(url)
		empleado.refresh_from_db()
		self.assertEqual(empleado.activo, "SI")
		self.assertIsNone(empleado.fecha_baja)

	def test_baja_repetida_no_reactiva(self):
		# Antes el mismo botón alternaba el estado: una página vieja reactivaba al empleado.
		empleado = self.crear_empleado()
		url = reverse("empleados:baja", args=[empleado.id_empleado])
		self.client.post(url)
		self.client.post(url)
		empleado.refresh_from_db()
		self.assertEqual(empleado.activo, "NO")

	def test_reactivar_repetido_no_da_de_baja(self):
		empleado = self.crear_empleado()
		url = reverse("empleados:reactivar", args=[empleado.id_empleado])
		self.client.post(url)
		empleado.refresh_from_db()
		self.assertEqual(empleado.activo, "SI")

	def test_no_se_puede_dar_de_baja_al_ultimo_administrador(self):
		otro_admin = crear_usuario(20333444, "Otro", "Admin", "Administrador")
		yo = Empleado.objects.get(nombre_usuario="admint")
		# Con dos administradores se puede dar de baja a uno.
		self.client.post(reverse("empleados:baja", args=[otro_admin.id_empleado]))
		otro_admin.refresh_from_db()
		self.assertEqual(otro_admin.activo, "NO")
		# Ahora "yo" es el único administrador; tampoco puedo darme de baja.
		self.client.post(reverse("empleados:baja", args=[yo.id_empleado]))
		yo.refresh_from_db()
		self.assertEqual(yo.activo, "SI")

	def test_next_externo_se_ignora(self):
		empleado = self.crear_empleado()
		respuesta = self.client.post(
			reverse("empleados:baja", args=[empleado.id_empleado]),
			{"next": "https://sitio-malicioso.example/"},
		)
		self.assertRedirects(respuesta, reverse("empleados:panel"))

	def test_alta_ignora_campo_activo(self):
		self.client.post(
			reverse("empleados:alta"),
			{
				"nombre": "Sofía",
				"apellido": "López",
				"dni": "55443322",
				"fecha_alta": "2025-01-15",
				"activo": "NO",
				"correo": "sofia@mail.com",
				"id_perfil": Perfil.objects.get(nombre_perfil="Empleado").pk,
			},
		)
		self.assertEqual(Empleado.objects.get(dni="55443322").activo, "SI")
