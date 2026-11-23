"""ABM (CRUD) de las tablas maestras del proceso: clientes, categorías y vehículos.
No hay borrado físico: la baja es lógica (ESTADO = INACTIVO) y se puede reactivar."""
from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from miprimerapp.models import CategoriaVehiculo, Cliente, Vehiculo
from usuarios.seguridad import permiso_requerido

from .forms import CategoriaForm, ClienteForm, VehiculoForm


def _estado(request):
    estado = request.GET.get("estado", "ACTIVO")
    return estado if estado in {"ACTIVO", "INACTIVO", "todos"} else "ACTIVO"


def _formulario(request, form, titulo, eyebrow, volver, boton):
    return render(
        request,
        "abm/formulario.html",
        {"form": form, "titulo": titulo, "eyebrow": eyebrow, "volver": volver, "boton": boton},
    )


# ------------------------------------------------------------------ Clientes
@permiso_requerido("clientes.gestionar")
def clientes(request):
    lista = Cliente.objects.prefetch_related("telefonos").order_by("apellido", "nombre")
    q = request.GET.get("q", "").strip()
    estado = _estado(request)
    if q:
        lista = lista.filter(Q(apellido__icontains=q) | Q(nombre__icontains=q) | Q(dni__icontains=q) | Q(correo_electronico__icontains=q))
    if estado != "todos":
        lista = lista.filter(estado=estado)
    return render(request, "abm/clientes.html", {"clientes": lista, "q": q, "estado": estado})


@permiso_requerido("clientes.gestionar")
def cliente_alta(request):
    form = ClienteForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        cliente = form.save()
        messages.success(request, f"Se registró el cliente {cliente.apellido}, {cliente.nombre}.")
        return redirect(request.GET.get("next") or "alquileres:clientes")
    return _formulario(request, form, "Nuevo cliente", "Clientes / Alta", "alquileres:clientes", "Guardar cliente")


@permiso_requerido("clientes.gestionar")
def cliente_editar(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    form = ClienteForm(request.POST or None, instance=cliente)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Se guardaron los cambios de {cliente.apellido}, {cliente.nombre}.")
        return redirect("alquileres:clientes")
    return _formulario(request, form, f"Editar cliente: {cliente.apellido}, {cliente.nombre}", "Clientes / Modificación", "alquileres:clientes", "Guardar cambios")


@require_POST
@permiso_requerido("clientes.gestionar")
def cliente_estado(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if cliente.estado == "ACTIVO" and cliente.contratos.filter(estado="CONFIRMADO").exists():
        messages.error(request, "No se puede dar de baja: el cliente tiene un alquiler en curso.")
        return redirect("alquileres:clientes")
    cliente.estado = "INACTIVO" if cliente.estado == "ACTIVO" else "ACTIVO"
    cliente.save(update_fields=["estado"])
    messages.success(request, f"{cliente.apellido}, {cliente.nombre} quedó {cliente.get_estado_display().lower()}.")
    return redirect("alquileres:clientes")


# ------------------------------------------------------------------ Categorías
@permiso_requerido("vehiculos.gestionar")
def categorias(request):
    estado = _estado(request)
    lista = CategoriaVehiculo.objects.annotate(total_vehiculos=Count("vehiculos")).order_by("nombre_categoria")
    if estado != "todos":
        lista = lista.filter(estado=estado)
    return render(request, "abm/categorias.html", {"categorias": lista, "estado": estado})


@permiso_requerido("vehiculos.gestionar")
def categoria_alta(request):
    form = CategoriaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        categoria = form.save()
        messages.success(request, f"Se registró la categoría {categoria.nombre_categoria}.")
        return redirect("alquileres:categorias")
    return _formulario(request, form, "Nueva categoría de vehículo", "Flota / Categorías / Alta", "alquileres:categorias", "Guardar categoría")


@permiso_requerido("vehiculos.gestionar")
def categoria_editar(request, pk):
    categoria = get_object_or_404(CategoriaVehiculo, pk=pk)
    form = CategoriaForm(request.POST or None, instance=categoria)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Se guardaron los cambios de la categoría {categoria.nombre_categoria}.")
        return redirect("alquileres:categorias")
    return _formulario(request, form, f"Editar categoría: {categoria.nombre_categoria}", "Flota / Categorías / Modificación", "alquileres:categorias", "Guardar cambios")


@require_POST
@permiso_requerido("vehiculos.gestionar")
def categoria_estado(request, pk):
    categoria = get_object_or_404(CategoriaVehiculo, pk=pk)
    if categoria.estado == "ACTIVO" and categoria.vehiculos.filter(estado="ACTIVO").exists():
        messages.error(request, "No se puede dar de baja: hay vehículos activos en esta categoría.")
        return redirect("alquileres:categorias")
    categoria.estado = "INACTIVO" if categoria.estado == "ACTIVO" else "ACTIVO"
    categoria.save(update_fields=["estado"])
    messages.success(request, f"La categoría {categoria.nombre_categoria} quedó {categoria.get_estado_display().lower()}.")
    return redirect("alquileres:categorias")


# ------------------------------------------------------------------ Vehículos
@permiso_requerido("vehiculos.gestionar")
def vehiculos(request):
    lista = Vehiculo.objects.select_related("id_categoria").order_by("patente")
    q = request.GET.get("q", "").strip()
    estado = _estado(request)
    operativo = request.GET.get("operativo", "")
    if q:
        lista = lista.filter(Q(patente__icontains=q) | Q(marca__icontains=q) | Q(modelo__icontains=q))
    if estado != "todos":
        lista = lista.filter(estado=estado)
    if operativo in dict(Vehiculo.ESTADO_OPERATIVO):
        lista = lista.filter(estado_operativo=operativo)
    return render(
        request,
        "abm/vehiculos.html",
        {"vehiculos": lista, "q": q, "estado": estado, "operativo": operativo, "estados_operativos": Vehiculo.ESTADO_OPERATIVO},
    )


@permiso_requerido("vehiculos.gestionar")
def vehiculo_alta(request):
    form = VehiculoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        vehiculo = form.save()
        messages.success(request, f"Se registró el vehículo {vehiculo.patente}.")
        return redirect("alquileres:vehiculos")
    return _formulario(request, form, "Nuevo vehículo", "Flota / Vehículos / Alta", "alquileres:vehiculos", "Guardar vehículo")


@permiso_requerido("vehiculos.gestionar")
def vehiculo_editar(request, pk):
    vehiculo = get_object_or_404(Vehiculo, pk=pk)
    form = VehiculoForm(request.POST or None, instance=vehiculo)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Se guardaron los cambios del vehículo {vehiculo.patente}.")
        return redirect("alquileres:vehiculos")
    return _formulario(request, form, f"Editar vehículo: {vehiculo.patente}", "Flota / Vehículos / Modificación", "alquileres:vehiculos", "Guardar cambios")


@require_POST
@permiso_requerido("vehiculos.gestionar")
def vehiculo_estado(request, pk):
    vehiculo = get_object_or_404(Vehiculo, pk=pk)
    if vehiculo.estado == "ACTIVO" and vehiculo.estado_operativo == "ALQUILADO":
        messages.error(request, "No se puede dar de baja un vehículo que está alquilado.")
        return redirect("alquileres:vehiculos")
    if vehiculo.estado == "INACTIVO" and vehiculo.id_categoria.estado != "ACTIVO":
        messages.error(request, "Primero reactivá la categoría del vehículo.")
        return redirect("alquileres:vehiculos")
    vehiculo.estado = "INACTIVO" if vehiculo.estado == "ACTIVO" else "ACTIVO"
    vehiculo.save(update_fields=["estado"])
    messages.success(request, f"El vehículo {vehiculo.patente} quedó {vehiculo.get_estado_display().lower()}.")
    return redirect("alquileres:vehiculos")
