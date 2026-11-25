from django import forms

from .models import Empleado


class EmpleadoForm(forms.ModelForm):
    class Meta:
        model = Empleado
        fields = [
            "nombre",
            "apellido",
            "dni",
            "fecha_alta",
            "correo",
            "id_perfil",
        ]
        labels = {
            "nombre": "Nombre",
            "apellido": "Apellido",
            "dni": "DNI",
            "fecha_alta": "Fecha de alta",
            "correo": "Correo electrónico",
            "id_perfil": "Perfil de acceso",
        }
        help_texts = {
            "dni": "Debe ser único para cada empleado.",
            "correo": "Se usará para acceder a la cuenta del empleado.",
        }
        widgets = {
            "nombre": forms.TextInput(attrs={"autocomplete": "given-name"}),
            "apellido": forms.TextInput(attrs={"autocomplete": "family-name"}),
            "dni": forms.TextInput(attrs={"autocomplete": "off"}),
            "fecha_alta": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields["correo"].required = True
            self.fields["id_perfil"].required = True

    def clean_dni(self):
        dni = self.cleaned_data["dni"]
        if self.cleaned_data.get("correo") or self.cleaned_data.get("id_perfil"):
            if not dni.isdigit() or not 1000000 <= int(dni) <= 99999999:
                raise forms.ValidationError("El DNI debe tener 7 u 8 dígitos.")
        if not dni:
            raise forms.ValidationError("El DNI debe tener 7 u 8 dígitos.")
        return dni


class EmpleadoModificarForm(forms.ModelForm):
    class Meta:
        model = Empleado
        fields = ["correo"]
        labels = {"correo": "Correo electrónico"}
        help_texts = {
            "correo": "Solo se permite modificar el correo electrónico.",
        }
        widgets = {
            "correo": forms.EmailInput(attrs={"autocomplete": "email"}),
        }

