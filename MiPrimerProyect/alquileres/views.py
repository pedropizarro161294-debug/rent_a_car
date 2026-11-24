"""Proceso de alquiler: registrar, consultar, ver detalle, finalizar, anular y comprobante."""
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.template.defaultfilters import floatformat
from django.utils import timezone
from django.views.decorators.http import require_POST

from miprimerapp.models import ContratoAlquiler
from usuarios.seguridad import permiso_requerido

from . import servicios
from .forms import AlquilerForm, AnulacionForm, ConsultaAlquilerForm


@permiso_requerido("alquileres.registrar")
def registrar(request):
    form = AlquilerForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        datos = form.cleaned_data
        try:
            contrato = servicios.registrar_alquiler(
                cliente=datos["id_cliente"],
                vehiculos=datos["vehiculos"],
                fecha_inicio=datos["fecha_inicio"],
                fecha_fin=datos["fecha_fin"],
                porcentaje_descuento=datos["porcentaje_descuento"],
                condiciones=datos["condiciones"],
                usuario=request.usuario,
            )
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, f"Se registró el alquiler {contrato.numero_contrato} por un total de ${floatformat(contrato.monto_total, '2g')}.")
            return redirect("alquileres:detalle", pk=contrato.pk)
    # Tarifas para el cálculo en pantalla (el cálculo que vale es el del servidor).
    vehiculos = form.fields["vehiculos"].queryset
    tarifas = {str(v.pk): str(v.id_categoria.tarifa) for v in vehiculos}
    # Períodos ya ocupados de cada vehículo, para avisar en pantalla según las fechas elegidas.
    ocupaciones = {}
    for d in servicios.reservas_confirmadas([v.pk for v in vehiculos]).select_related("id_contrato").order_by("id_contrato__fecha_inicio"):
        ocupaciones.setdefault(str(d.id_vehiculo_id), []).append(
            {"inicio": d.id_contrato.fecha_inicio.isoformat(), "fin": d.id_contrato.fecha_fin.isoformat()}
        )
    return render(
        request,
        "alquileres/registrar.html",
        {
            "form": form,
            "tarifas": tarifas,
            "ocupaciones": ocupaciones,
            "vehiculos_disponibles": vehiculos,
            "tasa_iva": servicios.TASA_IVA,
        },
    )


@permiso_requerido("alquileres.consultar")
def consulta(request):
    form = ConsultaAlquilerForm(request.GET or None)
    contratos = (
        ContratoAlquiler.objects.select_related("id_cliente", "id_empleado")
        .annotate(total_vehiculos=Count("detalles"))
        .order_by("-fecha_contrato")
    )
    if form.is_valid():
        d = form.cleaned_data
        if d["fecha_desde"]:
            contratos = contratos.filter(fecha_contrato__date__gte=d["fecha_desde"])
        if d["fecha_hasta"]:
            contratos = contratos.filter(fecha_contrato__date__lte=d["fecha_hasta"])
        if d["estado"]:
            contratos = contratos.filter(estado=d["estado"])
        if d["cliente"]:
            contratos = contratos.filter(id_cliente=d["cliente"])
        if d["vehiculo"]:
            contratos = contratos.filter(detalles__id_vehiculo=d["vehiculo"]).distinct()
    elif form.is_bound:
        contratos = contratos.none()
    totales = contratos.exclude(estado="ANULADO").aggregate(total=Sum("monto_total"))
    return render(
        request,
        "alquileres/consulta.html",
        {"form": form, "contratos": contratos, "total_facturado": totales["total"] or 0, "filtrado": bool(request.GET)},
    )


def _contrato(pk):
    return get_object_or_404(
        ContratoAlquiler.objects.select_related("id_cliente", "id_empleado", "id_empleado_anulacion"),
        pk=pk,
    )


@permiso_requerido("alquileres.consultar")
def detalle(request, pk):
    contrato = _contrato(pk)
    return render(
        request,
        "alquileres/detalle.html",
        {
            "contrato": contrato,
            "detalles": contrato.detalles.select_related("id_vehiculo__id_categoria"),
            "form_anulacion": AnulacionForm(),
            "puede_finalizar": contrato.fecha_inicio <= timezone.localdate(),
        },
    )


@permiso_requerido("alquileres.anular")
def anular(request, pk):
    contrato = _contrato(pk)
    form = AnulacionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            servicios.anular_alquiler(contrato, motivo=form.cleaned_data["motivo"], usuario=request.usuario)
        except ValidationError as error:
            messages.error(request, " ".join(error.messages))
        else:
            messages.success(request, f"Se anuló el alquiler {contrato.numero_contrato}. Los vehículos volvieron a estar disponibles.")
        return redirect("alquileres:detalle", pk=contrato.pk)
    if contrato.estado != "CONFIRMADO":
        messages.error(request, "Solo se puede anular un alquiler confirmado.")
        return redirect("alquileres:detalle", pk=contrato.pk)
    return render(request, "alquileres/anular.html", {"contrato": contrato, "form": form})


@require_POST
@permiso_requerido("alquileres.finalizar")
def finalizar(request, pk):
    contrato = _contrato(pk)
    try:
        servicios.finalizar_alquiler(contrato, usuario=request.usuario)
    except ValidationError as error:
        messages.error(request, " ".join(error.messages))
    else:
        messages.success(request, f"Se finalizó el alquiler {contrato.numero_contrato}. Los vehículos quedaron disponibles.")
    return redirect("alquileres:detalle", pk=contrato.pk)


@permiso_requerido("alquileres.comprobante")
def comprobante(request, pk):
    contrato = _contrato(pk)
    return render(
        request,
        "alquileres/comprobante.html",
        {"contrato": contrato, "detalles": contrato.detalles.select_related("id_vehiculo__id_categoria"), "tasa_iva": servicios.TASA_IVA},
    )
