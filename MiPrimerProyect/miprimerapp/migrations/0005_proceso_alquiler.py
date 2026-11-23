# Hito 3: el contrato de alquiler pasa a ser cabecera y se crea el detalle
# (un renglón por vehículo). Los contratos que ya existieran se migran al
# detalle antes de quitar la columna ID_VEHICULO de la cabecera.

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


def pasar_vehiculo_al_detalle(apps, schema_editor):
    Contrato = apps.get_model("miprimerapp", "ContratoAlquiler")
    Detalle = apps.get_model("miprimerapp", "DetalleContrato")
    for contrato in Contrato.objects.select_related("id_vehiculo__id_categoria"):
        dias = max((contrato.fecha_fin - contrato.fecha_inicio).days, 1)
        contrato.cantidad_dias = dias
        contrato.subtotal = contrato.monto_total
        contrato.numero_contrato = f"A-{contrato.id_contrato:08d}"
        if contrato.estado not in ("CONFIRMADO", "FINALIZADO", "ANULADO"):
            contrato.estado = "CONFIRMADO"
        contrato.save()
        if contrato.id_vehiculo_id:
            Detalle.objects.create(
                id_contrato=contrato,
                id_vehiculo=contrato.id_vehiculo,
                tarifa_diaria=contrato.id_vehiculo.id_categoria.tarifa,
                cantidad_dias=dias,
                subtotal=contrato.monto_total,
            )


class Migration(migrations.Migration):

    dependencies = [
        ("miprimerapp", "0004_reemplazar_estado_por_activo"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="contratoalquiler",
            options={
                "managed": True,
                "ordering": ["-id_contrato"],
                "verbose_name": "contrato de alquiler",
                "verbose_name_plural": "contratos de alquiler",
            },
        ),
        migrations.AddField(
            model_name="contratoalquiler",
            name="cantidad_dias",
            field=models.PositiveIntegerField(db_column="CANTIDAD_DIAS", default=1),
        ),
        migrations.AddField(
            model_name="contratoalquiler",
            name="fecha_anulacion",
            field=models.DateTimeField(
                blank=True, db_column="FECHA_ANULACION", null=True
            ),
        ),
        migrations.AddField(
            model_name="contratoalquiler",
            name="fecha_contrato",
            field=models.DateTimeField(
                db_column="FECHA_CONTRATO",
                default=django.utils.timezone.now,
                editable=False,
            ),
        ),
        migrations.AddField(
            model_name="contratoalquiler",
            name="fecha_finalizacion",
            field=models.DateTimeField(
                blank=True, db_column="FECHA_FINALIZACION", null=True
            ),
        ),
        migrations.AddField(
            model_name="contratoalquiler",
            name="id_empleado_anulacion",
            field=models.ForeignKey(
                blank=True,
                db_column="ID_EMPLEADO_ANULACION",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="contratos_anulados",
                to="miprimerapp.empleado",
            ),
        ),
        migrations.AddField(
            model_name="contratoalquiler",
            name="importe_descuento",
            field=models.DecimalField(
                db_column="IMPORTE_DESCUENTO",
                decimal_places=2,
                default=0,
                max_digits=12,
            ),
        ),
        migrations.AddField(
            model_name="contratoalquiler",
            name="importe_iva",
            field=models.DecimalField(
                db_column="IMPORTE_IVA", decimal_places=2, default=0, max_digits=12
            ),
        ),
        migrations.AddField(
            model_name="contratoalquiler",
            name="motivo_anulacion",
            field=models.CharField(
                blank=True, db_column="MOTIVO_ANULACION", max_length=255, null=True
            ),
        ),
        migrations.AddField(
            model_name="contratoalquiler",
            name="numero_contrato",
            field=models.CharField(
                blank=True,
                db_column="NUMERO_CONTRATO",
                editable=False,
                max_length=20,
                null=True,
                unique=True,
            ),
        ),
        migrations.AddField(
            model_name="contratoalquiler",
            name="porcentaje_descuento",
            field=models.DecimalField(
                db_column="PORCENTAJE_DESCUENTO",
                decimal_places=2,
                default=0,
                max_digits=5,
            ),
        ),
        migrations.AddField(
            model_name="contratoalquiler",
            name="subtotal",
            field=models.DecimalField(
                db_column="SUBTOTAL", decimal_places=2, default=0, max_digits=12
            ),
        ),
        migrations.AlterField(
            model_name="contratoalquiler",
            name="estado",
            field=models.CharField(
                choices=[
                    ("CONFIRMADO", "Confirmado"),
                    ("FINALIZADO", "Finalizado"),
                    ("ANULADO", "Anulado"),
                ],
                db_column="ESTADO",
                default="CONFIRMADO",
                max_length=15,
            ),
        ),
        migrations.AlterField(
            model_name="contratoalquiler",
            name="id_reserva",
            field=models.ForeignKey(
                blank=True,
                db_column="ID_RESERVA",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="contratos",
                to="miprimerapp.reserva",
            ),
        ),
        migrations.AlterField(
            model_name="contratoalquiler",
            name="monto_total",
            field=models.DecimalField(
                db_column="MONTO_TOTAL", decimal_places=2, default=0, max_digits=12
            ),
        ),
        migrations.CreateModel(
            name="DetalleContrato",
            fields=[
                (
                    "id_detalle",
                    models.AutoField(
                        db_column="ID_DETALLE", primary_key=True, serialize=False
                    ),
                ),
                (
                    "tarifa_diaria",
                    models.DecimalField(
                        db_column="TARIFA_DIARIA", decimal_places=2, max_digits=10
                    ),
                ),
                (
                    "cantidad_dias",
                    models.PositiveIntegerField(db_column="CANTIDAD_DIAS"),
                ),
                (
                    "subtotal",
                    models.DecimalField(
                        db_column="SUBTOTAL", decimal_places=2, max_digits=12
                    ),
                ),
                (
                    "id_contrato",
                    models.ForeignKey(
                        db_column="ID_CONTRATO",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="detalles",
                        to="miprimerapp.contratoalquiler",
                    ),
                ),
                (
                    "id_vehiculo",
                    models.ForeignKey(
                        db_column="ID_VEHICULO",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="detalles_contrato",
                        to="miprimerapp.vehiculo",
                    ),
                ),
            ],
            options={
                "db_table": "detalle_contrato",
                "managed": True,
                "constraints": [
                    models.UniqueConstraint(
                        fields=("id_contrato", "id_vehiculo"),
                        name="uq_detalle_contrato_vehiculo",
                    )
                ],
            },
        ),
        migrations.RunPython(pasar_vehiculo_al_detalle, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="contratoalquiler",
            name="id_vehiculo",
        ),
    ]
