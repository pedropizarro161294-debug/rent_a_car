from django import forms
from django.contrib.auth.password_validation import validate_password

from miprimerapp.models import Empleado


class BootstrapMixin:
    # Igual que en EmpleadoForm: les pone las clases de Bootstrap a los campos.
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            field.widget.attrs.setdefault("class", css)


class LoginForm(BootstrapMixin, forms.Form):
    nombre_usuario = forms.CharField(label="Usuario")
    clave = forms.CharField(label="Clave", widget=forms.PasswordInput)


class RestablecerClaveForm(BootstrapMixin, forms.Form):
    usuario = forms.ModelChoiceField(
        queryset=Empleado.objects.filter(activo="SI", nombre_usuario__isnull=False),
        label="Empleado",
        to_field_name="dni",
    )


class CambiarClaveForm(BootstrapMixin, forms.Form):
    clave_actual = forms.CharField(label="Clave actual", widget=forms.PasswordInput)
    clave_nueva = forms.CharField(label="Clave nueva", widget=forms.PasswordInput)
    clave_repetir = forms.CharField(label="Repetir clave nueva", widget=forms.PasswordInput)

    def __init__(self, usuario, *args, **kwargs):
        self.usuario = usuario
        super().__init__(*args, **kwargs)

    def clean_clave_actual(self):
        if not self.usuario.verificar_clave(self.cleaned_data["clave_actual"]):
            raise forms.ValidationError("La clave actual es incorrecta.")
        return self.cleaned_data["clave_actual"]

    def clean(self):
        datos = super().clean()
        nueva, repetir = datos.get("clave_nueva"), datos.get("clave_repetir")
        if nueva and repetir:
            if nueva != repetir:
                self.add_error("clave_repetir", "Las claves no coinciden.")
            elif nueva == datos.get("clave_actual"):
                self.add_error("clave_nueva", "Tiene que ser distinta de la actual.")
            else:
                try:
                    validate_password(nueva)  # usa AUTH_PASSWORD_VALIDATORS de settings.py
                except forms.ValidationError as e:
                    self.add_error("clave_nueva", e)
        return datos
