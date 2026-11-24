"""Lógica del proceso de alquiler.

Todas las operaciones que modifican varias tablas se hacen dentro de
transaction.atomic(): si algo falla, no queda nada a medias (se revierte todo).
"""
from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from miprimerapp.models import ContratoAlquiler, DetalleContrato, Vehiculo

TASA_IVA = Decimal("21")
CENTAVOS = Decimal("0.01")


def redondear(valor):
    return Decimal(valor).quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def calcular_dias(fecha_inicio, fecha_fin):
    """Días a cobrar: diferencia entre fechas; retirar y devolver el mismo día cuenta 1 día."""
    return max((fecha_fin - fecha_inicio).days, 1)


def calcular_importes(tarifas, dias, porcentaje_descuento):
    """Devuelve los subtotales por renglón y los totales del comprobante."""
    renglones = [redondear(Decimal(t) * dias) for t in tarifas]
    subtotal = redondear(sum(renglones, Decimal("0")))
    descuento = redondear(subtotal * Decimal(porcentaje_descuento) / 100)
    neto = subtotal - descuento
    iva = redondear(neto * TASA_IVA / 100)
    return {
        "renglones": renglones,
        "subtotal": subtotal,
        "importe_descuento": descuento,
        "importe_iva": iva,
        "monto_total": redondear(neto + iva),
    }


# Un vehículo se puede alquilar si está activo y en condiciones (no en mantenimiento
# ni fuera de servicio). Que esté "Alquilado" no impide alquilarlo para OTRAS fechas:
# lo que manda es que no haya otro alquiler confirmado que se superponga.
ESTADOS_ALQUILABLES = ("DISPONIBLE", "ALQUILADO")


def vehiculos_alquilables():
    return Vehiculo.objects.filter(estado="ACTIVO", estado_operativo__in=ESTADOS_ALQUILABLES)


def reservas_confirmadas(vehiculo_ids=None):
    """Renglones de alquileres confirmados (vehículo ocupado entre fecha_inicio y fecha_fin)."""
    detalles = DetalleContrato.objects.filter(id_contrato__estado="CONFIRMADO")
    if vehiculo_ids is not None:
        detalles = detalles.filter(id_vehiculo__in=vehiculo_ids)
    return detalles


def vehiculos_ocupados(fecha_inicio, fecha_fin, vehiculo_ids=None):
    """IDs de vehículos con un alquiler confirmado que se superpone con el período pedido.
    Se toman los extremos inclusive: el día de devolución el vehículo todavía está ocupado."""
    return set(
        reservas_confirmadas(vehiculo_ids)
        .filter(id_contrato__fecha_inicio__lte=fecha_fin, id_contrato__fecha_fin__gte=fecha_inicio)
        .values_list("id_vehiculo", flat=True)
    )


def registrar_alquiler(*, cliente, vehiculos, fecha_inicio, fecha_fin, porcentaje_descuento, condiciones, usuario):
    ids = sorted(v.pk for v in vehiculos)
    with transaction.atomic():
        # Bloquea los vehículos elegidos para que otro usuario no los alquile al mismo tiempo.
        bloqueados = list(
            Vehiculo.objects.select_for_update().select_related("id_categoria").filter(pk__in=ids).order_by("pk")
        )
        ocupados = vehiculos_ocupados(fecha_inicio, fecha_fin, ids)
        no_disponibles = [
            v
            for v in bloqueados
            if v.pk in ocupados or v.estado != "ACTIVO" or v.estado_operativo not in ESTADOS_ALQUILABLES
        ]
        if len(bloqueados) != len(ids) or no_disponibles:
            nombres = ", ".join(v.patente for v in no_disponibles) or "uno de los vehículos"
            raise ValidationError(f"No está disponible en esas fechas: {nombres}. Volvé a elegir los vehículos.")

        dias = calcular_dias(fecha_inicio, fecha_fin)
        importes = calcular_importes([v.id_categoria.tarifa for v in bloqueados], dias, porcentaje_descuento)

        contrato = ContratoAlquiler.objects.create(
            id_cliente=cliente,
            id_empleado=usuario,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            cantidad_dias=dias,
            subtotal=importes["subtotal"],
            porcentaje_descuento=porcentaje_descuento,
            importe_descuento=importes["importe_descuento"],
            importe_iva=importes["importe_iva"],
            monto_total=importes["monto_total"],
            condiciones=condiciones or None,
            estado="CONFIRMADO",
        )
        # Número de comprobante automático a partir del ID.
        contrato.numero_contrato = f"A-{contrato.id_contrato:08d}"
        contrato.save(update_fields=["numero_contrato"])

        for vehiculo, subtotal in zip(bloqueados, importes["renglones"]):
            DetalleContrato.objects.create(
                id_contrato=contrato,
                id_vehiculo=vehiculo,
                tarifa_diaria=vehiculo.id_categoria.tarifa,
                cantidad_dias=dias,
                subtotal=subtotal,
            )
        # "Alquilado" = el vehículo tiene al menos un alquiler confirmado (en curso o próximo).
        Vehiculo.objects.filter(pk__in=ids).update(estado_operativo="ALQUILADO")
    return contrato


def _liberar_vehiculos(contrato):
    """Vuelve a "Disponible" los vehículos que ya no tienen ningún otro alquiler confirmado."""
    ids = set(contrato.detalles.values_list("id_vehiculo", flat=True))
    siguen_reservados = set(reservas_confirmadas(ids).exclude(id_contrato=contrato).values_list("id_vehiculo", flat=True))
    Vehiculo.objects.select_for_update().filter(pk__in=ids - siguen_reservados, estado_operativo="ALQUILADO").update(
        estado_operativo="DISPONIBLE"
    )


def anular_alquiler(contrato, *, motivo, usuario):
    with transaction.atomic():
        contrato = ContratoAlquiler.objects.select_for_update().get(pk=contrato.pk)
        if contrato.estado != "CONFIRMADO":
            raise ValidationError("Solo se puede anular un alquiler confirmado.")
        motivo = (motivo or "").strip()
        if len(motivo) < 5:
            raise ValidationError("Indicá el motivo de la anulación (al menos 5 caracteres).")
        contrato.estado = "ANULADO"
        contrato.fecha_anulacion = timezone.now()
        contrato.motivo_anulacion = motivo
        contrato.id_empleado_anulacion = usuario
        contrato.save(update_fields=["estado", "fecha_anulacion", "motivo_anulacion", "id_empleado_anulacion"])
        # Revierte el movimiento: los vehículos vuelven a estar disponibles.
        _liberar_vehiculos(contrato)
    return contrato


def finalizar_alquiler(contrato, *, usuario):
    with transaction.atomic():
        contrato = ContratoAlquiler.objects.select_for_update().get(pk=contrato.pk)
        if contrato.estado != "CONFIRMADO":
            raise ValidationError("Solo se puede finalizar un alquiler confirmado.")
        if contrato.fecha_inicio > timezone.localdate():
            raise ValidationError(
                f"No se puede finalizar antes de la fecha de retiro ({contrato.fecha_inicio:%d/%m/%Y}): "
                "el cliente todavía no se llevó el vehículo. Si no lo va a retirar, anulá el alquiler."
            )
        contrato.estado = "FINALIZADO"
        contrato.fecha_finalizacion = timezone.now()
        contrato.save(update_fields=["estado", "fecha_finalizacion"])
        _liberar_vehiculos(contrato)
    return contrato
