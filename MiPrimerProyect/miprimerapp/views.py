from django.contrib import messages
from django.db.models import Q
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import EmpleadoForm, EmpleadoModificarForm
from .models import Empleado
from usuarios.models import Perfil
from usuarios.seguridad import generar_clave_temporal, permiso_requerido


@permiso_requerido("empleados.ver")
def panel_empleados(request):
	empleados = Empleado.objects.select_related("id_perfil").all()
	busqueda = request.GET.get("q", "").strip()
	estado = request.GET.get("estado", "todos")
	puede_ver_perfiles = "usuarios.ver" in request.usuario.permisos()
	perfiles = Perfil.objects.order_by("nombre_perfil") if puede_ver_perfiles else Perfil.objects.none()
	perfil = request.GET.get("perfil", "todos") if puede_ver_perfiles else "todos"

	if busqueda:
		coincidencias = (
			Q(nombre__icontains=busqueda)
			| Q(apellido__icontains=busqueda)
			| Q(dni__icontains=busqueda)
		)
		if puede_ver_perfiles:
			coincidencias |= (
				Q(correo__icontains=busqueda)
				| Q(nombre_usuario__icontains=busqueda)
				| Q(id_perfil__nombre_perfil__icontains=busqueda)
			)
		empleados = empleados.filter(coincidencias)
	if estado in {"ACTIVO", "INACTIVO"}:
		empleados = empleados.filter(activo="SI" if estado == "ACTIVO" else "NO")
	else:
		estado = "todos"
	if perfil == "sin":
		empleados = empleados.filter(id_perfil__isnull=True)
	elif perfil.isdigit() and perfiles.filter(pk=perfil).exists():
		empleados = empleados.filter(id_perfil_id=int(perfil))
	else:
		perfil = "todos"

	return render(
		request,
		"empleados/panel_empleados.html",
		{
			"empleados": empleados,
			"busqueda": busqueda,
			"estado_seleccionado": estado,
			"perfiles": perfiles,
			"perfil_seleccionado": perfil,
			"total_empleados": Empleado.objects.count(),
			"empleados_activos": Empleado.objects.filter(activo="SI").count(),
			"empleados_inactivos": Empleado.objects.filter(activo="NO").count(),
		},
	)


@permiso_requerido("empleados.gestionar")
def alta_empleado(request):
	form = EmpleadoForm(request.POST or None)
	if request.method == "POST" and form.is_valid():
		empleado = form.save(commit=False)
		clave = generar_clave_temporal()
		empleado.set_clave(clave, debe_cambiar=True)
		empleado.save()
		return render(
			request,
			"usuarios/clave_generada.html",
			{"u": empleado, "clave": clave, "accion": "Alta de empleado"},
		)
	return render(request, "empleados/alta_empleados.html", {"form": form})


@permiso_requerido("empleados.gestionar")
def editar_empleado(request, empleado_id):
	empleado = get_object_or_404(Empleado, pk=empleado_id)
	form = EmpleadoModificarForm(request.POST or None, instance=empleado)
	if request.method == "POST" and form.is_valid():
		form.save()
		messages.success(request, f"Guardaste los cambios de {empleado.nombre} {empleado.apellido}.")
		return redirect("empleados:panel")
	return render(
		request,
		"empleados/editar_empleado.html",
		{"form": form, "empleado": empleado},
	)


@permiso_requerido("empleados.gestionar")
def baja_empleados(request):
	empleados = Empleado.objects.filter(activo="SI")
	return render(request, "empleados/baja_empleados.html", {"empleados": empleados})


PERMISO_GESTION = "empleados.gestionar"


def _destino_seguro(request):
	"""Devuelve el `next` del formulario solo si apunta a este mismo sitio."""
	destino = request.POST.get("next") or request.GET.get("next")
	if destino and url_has_allowed_host_and_scheme(
		destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()
	):
		return destino
	return reverse("empleados:panel")


def _es_administrador(empleado):
	return empleado.activo == "SI" and empleado.tiene_permiso(PERMISO_GESTION)


def _administradores_activos():
	return Empleado.objects.filter(
		activo="SI",
		id_perfil__perfil_permisos__id_permiso__nombre_permiso=PERMISO_GESTION,
	)


def _confirmar(request, empleado, accion):
	return render(
		request,
		"empleados/confirmar_estado.html",
		{"empleado": empleado, "accion": accion, "next": _destino_seguro(request)},
	)


@permiso_requerido(PERMISO_GESTION)
def dar_de_baja_empleado(request, empleado_id):
	empleado = get_object_or_404(Empleado.objects.select_related("id_perfil"), pk=empleado_id)
	destino = _destino_seguro(request)
	if empleado.activo != "SI":
		messages.info(request, f"{empleado.nombre} {empleado.apellido} ya estaba dado de baja.")
		return redirect(destino)
	if empleado.dni == str(request.usuario.dni):
		messages.error(request, "No podés darte de baja a vos mismo.")
		return redirect(destino)
	if request.method != "POST":
		return _confirmar(request, empleado, "baja")

	with transaction.atomic():
		# Bloqueamos las filas de los administradores activos para que dos bajas
		# simultáneas no dejen el sistema sin nadie que pueda gestionar empleados.
		administradores = list(_administradores_activos().select_for_update().values_list("pk", flat=True))
		empleado = Empleado.objects.select_for_update().get(pk=empleado.pk)
		if empleado.activo != "SI":
			messages.info(request, f"{empleado.nombre} {empleado.apellido} ya estaba dado de baja.")
			return redirect(destino)
		if empleado.pk in administradores and len(administradores) <= 1:
			messages.error(request, "Es el único administrador activo. Para darlo de baja, primero asigná otro.")
			return redirect(destino)
		empleado.dar_de_baja()
	messages.success(request, f"Diste de baja a {empleado.nombre} {empleado.apellido}.")
	return redirect(destino)


@permiso_requerido(PERMISO_GESTION)
def reactivar_empleado(request, empleado_id):
	empleado = get_object_or_404(Empleado.objects.select_related("id_perfil"), pk=empleado_id)
	destino = _destino_seguro(request)
	if empleado.activo == "SI":
		messages.info(request, f"{empleado.nombre} {empleado.apellido} ya estaba activo.")
		return redirect(destino)
	if request.method != "POST":
		return _confirmar(request, empleado, "reactivar")

	with transaction.atomic():
		empleado = Empleado.objects.select_for_update().get(pk=empleado.pk)
		if empleado.activo == "SI":
			messages.info(request, f"{empleado.nombre} {empleado.apellido} ya estaba activo.")
			return redirect(destino)
		empleado.reactivar()
	messages.success(request, f"Reactivaste a {empleado.nombre} {empleado.apellido}.")
	return redirect(destino)
