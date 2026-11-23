import unicodedata

from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone


ESTADO_REGISTRO = [
    ("ACTIVO", "Activo"),
    ("INACTIVO", "Inactivo"),
]

OPCIONES_ACTIVO = [
    ("SI", "Sí"),
    ("NO", "No"),
]


class CategoriaVehiculo(models.Model):
    id_categoria = models.AutoField(db_column="ID_CATEGORIA", primary_key=True)
    nombre_categoria = models.CharField(db_column="NOMBRE_CATEGORIA", max_length=50, unique=True)
    tarifa = models.DecimalField(db_column="TARIFA", max_digits=10, decimal_places=2)
    tamanio = models.CharField(db_column="TAMANIO", max_length=30)
    equipamiento = models.CharField(db_column="EQUIPAMIENTO", max_length=255, blank=True, null=True)
    precio = models.DecimalField(db_column="PRECIO", max_digits=10, decimal_places=2)
    estado = models.CharField(db_column="ESTADO", max_length=10, choices=ESTADO_REGISTRO, default="ACTIVO")
    fecha_alta = models.DateField(db_column="FECHA_ALTA", auto_now_add=True)

    class Meta:
        managed = True
        db_table = "categoria_vehiculo"
        verbose_name = "categoría de vehículo"
        verbose_name_plural = "categorías de vehículo"

    def __str__(self):
        return self.nombre_categoria


class Cliente(models.Model):
    id_cliente = models.AutoField(db_column="ID_CLIENTE", primary_key=True)
    dni = models.CharField(db_column="DNI", max_length=15, unique=True)  # clave candidata
    nombre = models.CharField(db_column="NOMBRE", max_length=50)
    apellido = models.CharField(db_column="APELLIDO", max_length=50)
    correo_electronico = models.EmailField(db_column="CORREO_ELECTRONICO", max_length=100, blank=True, null=True)
    domicilio = models.CharField(db_column="DOMICILIO", max_length=150, blank=True, null=True)
    fecha_alta_cliente = models.DateField(db_column="FECHA_ALTA_CLIENTE", auto_now_add=True)
    estado = models.CharField(db_column="ESTADO", max_length=10, choices=ESTADO_REGISTRO, default="ACTIVO")

    class Meta:
        managed = True
        db_table = "cliente"

    def __str__(self):
        return f"{self.apellido}, {self.nombre} ({self.dni})"


class TelefonoCliente(models.Model):
    pk = models.CompositePrimaryKey("id_cliente", "telefono")
    id_cliente = models.ForeignKey(Cliente, models.CASCADE, db_column="ID_CLIENTE", related_name="telefonos")
    telefono = models.CharField(db_column="TELEFONO", max_length=20)

    class Meta:
        managed = True
        db_table = "telefono_cliente"
        verbose_name = "teléfono de cliente"
        verbose_name_plural = "teléfonos de cliente"

    def __str__(self):
        return self.telefono


class Empleado(models.Model):
    id_empleado = models.AutoField(db_column="ID_EMPLEADO", primary_key=True)
    nombre = models.CharField(db_column="NOMBRE", max_length=50)
    apellido = models.CharField(db_column="APELLIDO", max_length=50)
    dni = models.CharField(db_column="DNI", max_length=15, unique=True)  # clave candidata
    fecha_alta = models.DateField(db_column="FECHA_ALTA")
    activo = models.CharField(db_column="ACTIVO", max_length=2, choices=OPCIONES_ACTIVO, default="SI")
    correo = models.EmailField(db_column="CORREO", max_length=100, unique=True, blank=True, null=True)
    nombre_usuario = models.CharField(db_column="NOMBRE_USUARIO", max_length=60, unique=True, blank=True, null=True, editable=False)
    clave = models.CharField(db_column="CLAVE", max_length=128, blank=True, null=True)
    debe_cambiar_clave = models.BooleanField(db_column="DEBE_CAMBIAR_CLAVE", default=False)
    fecha_ultima_modificacion = models.DateTimeField(db_column="FECHA_ULTIMA_MODIFICACION", auto_now=True, blank=True, null=True)
    fecha_baja = models.DateTimeField(db_column="FECHA_BAJA", blank=True, null=True)
    id_perfil = models.ForeignKey(
        "usuarios.Perfil",
        models.PROTECT,
        db_column="ID_PERFIL",
        related_name="empleados",
        blank=True,
        null=True,
    )

    class Meta:
        managed = True
        db_table = "empleados"
        ordering = ["apellido", "nombre"]

    def __str__(self):
        return f"{self.apellido}, {self.nombre}"

    def save(self, *args, **kwargs):
        if not self.nombre_usuario and self.id_perfil_id:
            base = _limpiar(self.apellido) + _limpiar(self.nombre.split()[0])[:1]
            candidato, numero = base, 1
            while Empleado.objects.filter(nombre_usuario=candidato).exclude(pk=self.pk).exists():
                numero += 1
                candidato = f"{base}{numero}"
            self.nombre_usuario = candidato
        super().save(*args, **kwargs)

    def set_clave(self, clave_plana, debe_cambiar):
        self.clave = make_password(clave_plana)
        self.debe_cambiar_clave = debe_cambiar

    def verificar_clave(self, clave_plana):
        return bool(self.clave) and check_password(clave_plana, self.clave)

    def dar_de_baja(self):
        self.activo = "NO"
        self.fecha_baja = timezone.now()
        self.save(update_fields=["activo", "fecha_baja", "fecha_ultima_modificacion"])

    def permisos(self):
        if not self.id_perfil_id:
            return set()
        from usuarios.models import Permiso

        return set(
            Permiso.objects.filter(perfil_permisos__id_perfil=self.id_perfil)
            .values_list("nombre_permiso", flat=True)
        )

    def tiene_permiso(self, nombre_permiso):
        return nombre_permiso in self.permisos()


def _limpiar(texto):
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return "".join(caracter for caracter in sin_tildes.lower() if caracter.isalnum())


class Vehiculo(models.Model):
    ESTADO_OPERATIVO = [
        ("DISPONIBLE", "Disponible"),
        ("ALQUILADO", "Alquilado"),
        ("EN_MANTENIMIENTO", "En mantenimiento"),
        ("FUERA_DE_SERVICIO", "Fuera de servicio"),
    ]

    id_vehiculo = models.AutoField(db_column="ID_VEHICULO", primary_key=True)
    patente = models.CharField(db_column="PATENTE", max_length=10, unique=True)  # clave candidata
    marca = models.CharField(db_column="MARCA", max_length=50)
    modelo = models.CharField(db_column="MODELO", max_length=50)
    estado_operativo = models.CharField(db_column="ESTADO_OPERATIVO", max_length=20, choices=ESTADO_OPERATIVO, default="DISPONIBLE")
    id_categoria = models.ForeignKey(CategoriaVehiculo, models.PROTECT, db_column="ID_CATEGORIA", related_name="vehiculos")
    fecha_alta = models.DateField(db_column="FECHA_ALTA", auto_now_add=True)
    estado = models.CharField(db_column="ESTADO", max_length=10, choices=ESTADO_REGISTRO, default="ACTIVO")

    class Meta:
        managed = True
        db_table = "vehiculo"

    def __str__(self):
        return f"{self.patente} - {self.marca} {self.modelo}"


class Reserva(models.Model):
    ESTADO_RESERVA = [
        ("PENDIENTE", "Pendiente"),
        ("CONFIRMADA", "Confirmada"),
        ("CANCELADA", "Cancelada"),
        ("FINALIZADA", "Finalizada"),
    ]

    id_reserva = models.AutoField(db_column="ID_RESERVA", primary_key=True)
    id_cliente = models.ForeignKey(Cliente, models.PROTECT, db_column="ID_CLIENTE", related_name="reservas")
    id_categoria = models.ForeignKey(CategoriaVehiculo, models.PROTECT, db_column="ID_CATEGORIA", related_name="reservas")
    id_empleado = models.ForeignKey(Empleado, models.PROTECT, db_column="ID_EMPLEADO", related_name="reservas")
    fecha_reserva = models.DateField(db_column="FECHA_RESERVA")
    fecha_retiro = models.DateField(db_column="FECHA_RETIRO")
    fecha_devolucion = models.DateField(db_column="FECHA_DEVOLUCION")
    lugar_retiro = models.CharField(db_column="LUGAR_RETIRO", max_length=100)
    costo_estimado = models.DecimalField(db_column="COSTO_ESTIMADO", max_digits=12, decimal_places=2)  # atributo derivado
    estado = models.CharField(db_column="ESTADO", max_length=15, choices=ESTADO_RESERVA, default="PENDIENTE")

    class Meta:
        managed = True
        db_table = "reserva"

    def __str__(self):
        return f"Reserva {self.id_reserva}"


class Pago(models.Model):
    MEDIO_PAGO = [
        ("EFECTIVO", "Efectivo"),
        ("TARJETA", "Tarjeta"),
        ("TRANSFERENCIA", "Transferencia"),
    ]

    id_pago = models.AutoField(db_column="ID_PAGO", primary_key=True)
    id_reserva = models.ForeignKey(Reserva, models.PROTECT, db_column="ID_RESERVA", related_name="pagos")
    id_empleado = models.ForeignKey(Empleado, models.PROTECT, db_column="ID_EMPLEADO", related_name="pagos")
    importe = models.DecimalField(db_column="IMPORTE", max_digits=12, decimal_places=2)
    medio_pago = models.CharField(db_column="MEDIO_PAGO", max_length=15, choices=MEDIO_PAGO)
    datos_tarjeta = models.CharField(db_column="DATOS_TARJETA", max_length=100, blank=True, null=True)
    comprobante_bancario = models.CharField(db_column="COMPROBANTE_BANCARIO", max_length=100, blank=True, null=True)
    fecha_pago = models.DateField(db_column="FECHA_PAGO")
    estado = models.CharField(db_column="ESTADO", max_length=15, default="REGISTRADO")

    class Meta:
        managed = True
        db_table = "pago"

    def __str__(self):
        return f"Pago {self.id_pago} - ${self.importe}"


class ContratoAlquiler(models.Model):
    id_contrato = models.AutoField(db_column="ID_CONTRATO", primary_key=True)
    id_reserva = models.ForeignKey(Reserva, models.PROTECT, db_column="ID_RESERVA", related_name="contratos")
    id_cliente = models.ForeignKey(Cliente, models.PROTECT, db_column="ID_CLIENTE", related_name="contratos")
    id_vehiculo = models.ForeignKey(Vehiculo, models.PROTECT, db_column="ID_VEHICULO", related_name="contratos")
    id_empleado = models.ForeignKey(Empleado, models.PROTECT, db_column="ID_EMPLEADO", related_name="contratos")
    fecha_inicio = models.DateField(db_column="FECHA_INICIO")
    fecha_fin = models.DateField(db_column="FECHA_FIN")
    monto_total = models.DecimalField(db_column="MONTO_TOTAL", max_digits=12, decimal_places=2)
    condiciones = models.TextField(db_column="CONDICIONES", blank=True, null=True)
    estado = models.CharField(db_column="ESTADO", max_length=15, default="VIGENTE")
    fecha_alta = models.DateField(db_column="FECHA_ALTA", auto_now_add=True)

    class Meta:
        managed = True
        db_table = "contrato_alquiler"
        verbose_name = "contrato de alquiler"
        verbose_name_plural = "contratos de alquiler"

    def __str__(self):
        return f"Contrato {self.id_contrato}"


class Entrega(models.Model):
    id_entrega = models.AutoField(db_column="ID_ENTREGA", primary_key=True)
    # Relación 1:1 con el contrato: cada contrato tiene una sola entrega.
    id_contrato = models.OneToOneField(ContratoAlquiler, models.PROTECT, db_column="ID_CONTRATO", related_name="entrega")
    id_vehiculo = models.ForeignKey(Vehiculo, models.PROTECT, db_column="ID_VEHICULO", related_name="entregas")
    id_cliente = models.ForeignKey(Cliente, models.PROTECT, db_column="ID_CLIENTE", related_name="entregas")
    id_empleado = models.ForeignKey(Empleado, models.PROTECT, db_column="ID_EMPLEADO", related_name="entregas")
    fecha_entrega = models.DateTimeField(db_column="FECHA_ENTREGA")
    kilometraje = models.PositiveIntegerField(db_column="KILOMETRAJE")
    nivel_combustible = models.CharField(db_column="NIVEL_COMBUSTIBLE", max_length=20)
    estado_vehiculo = models.CharField(db_column="ESTADO_VEHICULO", max_length=255)
    estado = models.CharField(db_column="ESTADO", max_length=15, default="REALIZADA")

    class Meta:
        managed = True
        db_table = "entrega"

    def __str__(self):
        return f"Entrega {self.id_entrega}"


class Recepcion(models.Model):
    id_recepcion = models.AutoField(db_column="ID_RECEPCION", primary_key=True)
    # Relación 1:1 con el contrato: cada contrato finaliza en una sola recepción.
    id_contrato = models.OneToOneField(ContratoAlquiler, models.PROTECT, db_column="ID_CONTRATO", related_name="recepcion")
    id_vehiculo = models.ForeignKey(Vehiculo, models.PROTECT, db_column="ID_VEHICULO", related_name="recepciones")
    id_empleado = models.ForeignKey(Empleado, models.PROTECT, db_column="ID_EMPLEADO", related_name="recepciones")
    fecha_recepcion = models.DateTimeField(db_column="FECHA_RECEPCION")
    kilometraje = models.PositiveIntegerField(db_column="KILOMETRAJE")
    nivel_combustible = models.CharField(db_column="NIVEL_COMBUSTIBLE", max_length=20)
    estado_vehiculo = models.CharField(db_column="ESTADO_VEHICULO", max_length=255)
    informe_devolucion = models.TextField(db_column="INFORME_DEVOLUCION", blank=True, null=True)
    estado = models.CharField(db_column="ESTADO", max_length=15, default="REALIZADA")

    class Meta:
        managed = True
        db_table = "recepcion"
        verbose_name = "recepción"
        verbose_name_plural = "recepciones"

    def __str__(self):
        return f"Recepción {self.id_recepcion}"


class Mantenimiento(models.Model):
    TIPO_MANTENIMIENTO = [
        ("PREVENTIVO", "Preventivo"),
        ("CORRECTIVO", "Correctivo"),
    ]

    id_mantenimiento = models.AutoField(db_column="ID_MANTENIMIENTO", primary_key=True)
    id_vehiculo = models.ForeignKey(Vehiculo, models.PROTECT, db_column="ID_VEHICULO", related_name="mantenimientos")
    id_empleado = models.ForeignKey(Empleado, models.PROTECT, db_column="ID_EMPLEADO", related_name="mantenimientos")
    tipo_mantenimiento = models.CharField(db_column="TIPO_MANTENIMIENTO", max_length=15, choices=TIPO_MANTENIMIENTO)
    fecha_mantenimiento = models.DateField(db_column="FECHA_MANTENIMIENTO")
    reporte_falla = models.TextField(db_column="REPORTE_FALLA", blank=True, null=True)
    plan_mantenimiento = models.TextField(db_column="PLAN_MANTENIMIENTO", blank=True, null=True)
    descripcion = models.TextField(db_column="DESCRIPCION", blank=True, null=True)
    estado = models.CharField(db_column="ESTADO", max_length=15, default="PENDIENTE")

    class Meta:
        managed = True
        db_table = "mantenimiento"

    def __str__(self):
        return f"Mantenimiento {self.id_mantenimiento} - {self.id_vehiculo}"


class HistorialMantenimiento(models.Model):
    id_historial = models.AutoField(db_column="ID_HISTORIAL", primary_key=True)
    id_vehiculo = models.ForeignKey(Vehiculo, models.PROTECT, db_column="ID_VEHICULO", related_name="historial")
    # Relación 1:1: cada mantenimiento se registra una vez en el historial.
    id_mantenimiento = models.OneToOneField(Mantenimiento, models.PROTECT, db_column="ID_MANTENIMIENTO", related_name="historial")
    fecha = models.DateField(db_column="FECHA")
    detalle = models.TextField(db_column="DETALLE", blank=True, null=True)

    class Meta:
        managed = True
        db_table = "historial_mantenimiento"
        verbose_name = "historial de mantenimiento"
        verbose_name_plural = "historial de mantenimiento"

    def __str__(self):
        return f"Historial {self.id_historial}"
