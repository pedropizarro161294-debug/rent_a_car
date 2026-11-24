from datetime import timedelta
from decimal import Decimal

from django import forms
from django.utils import timezone

from miprimerapp.models import CategoriaVehiculo, Cliente, ContratoAlquiler, TelefonoCliente, Vehiculo

from . import servicios

MAX_DIAS = 90
MAX_DESCUENTO = Decimal("30")


# ---------------------------------------------------------------- ABM
class ClienteForm(forms.ModelForm):
    telefono = forms.CharField(label="Teléfono", max_length=20, required=False)

    class Meta:
        model = Cliente
        fields = ["dni", "apellido", "nombre", "correo_electronico", "domicilio"]
        labels = {
            "dni": "DNI",
            "apellido": "Apellido",
            "nombre": "Nombre",
            "correo_electronico": "Correo electrónico",
            "domicilio": "Domicilio",
        }
        help_texts = {"dni": "7 u 8 dígitos, sin puntos. No puede repetirse."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            primero = self.instance.telefonos.first()
            self.fields["telefono"].initial = primero.telefono if primero else ""

    def clean_dni(self):
        dni = self.cleaned_data["dni"].strip()
        if not dni.isdigit() or not 1000000 <= int(dni) <= 99999999:
            raise forms.ValidationError("El DNI debe tener 7 u 8 dígitos.")
        return dni

    def clean_telefono(self):
        telefono = self.cleaned_data["telefono"].strip()
        if telefono and not telefono.replace(" ", "").replace("-", "").replace("+", "").isdigit():
            raise forms.ValidationError("El teléfono solo puede tener números, espacios, guiones o +.")
        return telefono

    def save(self, commit=True):
        cliente = super().save(commit=commit)
        if commit:
            TelefonoCliente.objects.filter(id_cliente=cliente).delete()
            if self.cleaned_data.get("telefono"):
                TelefonoCliente.objects.create(id_cliente=cliente, telefono=self.cleaned_data["telefono"])
        return cliente


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = CategoriaVehiculo
        fields = ["nombre_categoria", "tamanio", "tarifa", "precio", "equipamiento"]
        labels = {
            "nombre_categoria": "Nombre de la categoría",
            "tamanio": "Tamaño",
            "tarifa": "Tarifa diaria ($)",
            "precio": "Precio de referencia ($)",
            "equipamiento": "Equipamiento",
        }
        help_texts = {"tarifa": "Es el importe por día que se cobra en el alquiler."}

    def clean_tarifa(self):
        tarifa = self.cleaned_data["tarifa"]
        if tarifa <= 0:
            raise forms.ValidationError("La tarifa debe ser mayor que cero.")
        return tarifa

    def clean_precio(self):
        precio = self.cleaned_data["precio"]
        if precio < 0:
            raise forms.ValidationError("El precio no puede ser negativo.")
        return precio


class VehiculoForm(forms.ModelForm):
    ESTADOS_MANUALES = [e for e in Vehiculo.ESTADO_OPERATIVO if e[0] != "ALQUILADO"]

    class Meta:
        model = Vehiculo
        fields = ["patente", "marca", "modelo", "id_categoria", "estado_operativo"]
        labels = {
            "patente": "Patente",
            "marca": "Marca",
            "modelo": "Modelo",
            "id_categoria": "Categoría",
            "estado_operativo": "Estado operativo",
        }
        help_texts = {"estado_operativo": "\"Alquilado\" lo asigna solo el proceso de alquiler."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["id_categoria"].queryset = CategoriaVehiculo.objects.filter(estado="ACTIVO").order_by("nombre_categoria")
        self.fields["id_categoria"].empty_label = "Elegí una categoría"
        if self.instance.pk and self.instance.estado_operativo == "ALQUILADO":
            # Mientras esté alquilado no se puede cambiar su estado a mano.
            self.fields["estado_operativo"].disabled = True
        else:
            self.fields["estado_operativo"].choices = self.ESTADOS_MANUALES

    def clean_patente(self):
        patente = self.cleaned_data["patente"].upper().replace(" ", "")
        if not 6 <= len(patente) <= 7 or not patente.isalnum():
            raise forms.ValidationError("La patente debe tener 6 o 7 letras y números (ej.: AB123CD).")
        return patente


# ---------------------------------------------------------------- Proceso
class VehiculosDisponiblesField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.patente} - {obj.marca} {obj.modelo} ({obj.id_categoria.nombre_categoria})"


class AlquilerForm(forms.Form):
    id_cliente = forms.ModelChoiceField(
        label="Cliente",
        queryset=Cliente.objects.none(),
        empty_label="Elegí un cliente",
    )
    fecha_inicio = forms.DateField(label="Fecha de retiro", widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    fecha_fin = forms.DateField(label="Fecha de devolución", widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    porcentaje_descuento = forms.DecimalField(
        label="Descuento (%)",
        min_value=0,
        max_value=MAX_DESCUENTO,
        max_digits=5,
        decimal_places=2,
        initial=0,
        help_text=f"Entre 0 y {MAX_DESCUENTO:.0f} %.",
    )
    vehiculos = VehiculosDisponiblesField(
        label="Vehículos a alquilar",
        queryset=Vehiculo.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        error_messages={"required": "Elegí al menos un vehículo."},
    )
    condiciones = forms.CharField(label="Observaciones / condiciones", required=False, widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["id_cliente"].queryset = Cliente.objects.filter(estado="ACTIVO").order_by("apellido", "nombre")
        self.fields["vehiculos"].queryset = (
            servicios.vehiculos_alquilables()
            .select_related("id_categoria")
            .order_by("id_categoria__nombre_categoria", "patente")
        )

    def clean(self):
        datos = super().clean()
        inicio, fin = datos.get("fecha_inicio"), datos.get("fecha_fin")
        hoy = timezone.localdate()
        if inicio and inicio < hoy:
            self.add_error("fecha_inicio", "La fecha de retiro no puede ser anterior a hoy.")
        if inicio and fin:
            if fin < inicio:
                self.add_error("fecha_fin", "La devolución no puede ser anterior al retiro.")
            elif fin - inicio > timedelta(days=MAX_DIAS):
                self.add_error("fecha_fin", f"El alquiler no puede superar {MAX_DIAS} días.")
            elif datos.get("vehiculos"):
                ocupados = servicios.vehiculos_ocupados(inicio, fin, [v.pk for v in datos["vehiculos"]])
                if ocupados:
                    patentes = ", ".join(v.patente for v in datos["vehiculos"] if v.pk in ocupados)
                    self.add_error("vehiculos", f"Ya está alquilado en esas fechas: {patentes}.")
        return datos


class AnulacionForm(forms.Form):
    motivo = forms.CharField(
        label="Motivo de la anulación",
        min_length=5,
        max_length=255,
        widget=forms.Textarea(attrs={"rows": 3}),
    )


class ConsultaAlquilerForm(forms.Form):
    fecha_desde = forms.DateField(label="Desde", required=False, widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    fecha_hasta = forms.DateField(label="Hasta", required=False, widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    estado = forms.ChoiceField(label="Estado", required=False, choices=[("", "Todos")] + ContratoAlquiler.ESTADO_CONTRATO)
    cliente = forms.ModelChoiceField(label="Cliente", required=False, queryset=Cliente.objects.none(), empty_label="Todos")
    vehiculo = forms.ModelChoiceField(label="Vehículo", required=False, queryset=Vehiculo.objects.none(), empty_label="Todos")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cliente"].queryset = Cliente.objects.order_by("apellido", "nombre")
        self.fields["vehiculo"].queryset = Vehiculo.objects.order_by("patente")

    def clean(self):
        datos = super().clean()
        desde, hasta = datos.get("fecha_desde"), datos.get("fecha_hasta")
        if desde and hasta and hasta < desde:
            self.add_error("fecha_hasta", "La fecha \"hasta\" no puede ser anterior a \"desde\".")
        return datos
