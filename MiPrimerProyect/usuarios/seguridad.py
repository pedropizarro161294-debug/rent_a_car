# Login por sesión, decorador de permisos y cambio de clave obligatorio.
import secrets
import string
from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse

from miprimerapp.models import Empleado

CLAVE_SESION = "usuario_dni"


def generar_clave_temporal(largo=10):
    caracteres = string.ascii_letters + string.digits
    return "".join(secrets.choice(caracteres) for _ in range(largo))


def permiso_requerido(nombre_permiso=None):
    """@permiso_requerido() = solo pide estar logueado.
    @permiso_requerido("usuarios.alta") = además pide ese permiso en el perfil."""
    def decorador(vista):
        @wraps(vista)
        def envoltura(request, *args, **kwargs):
            if request.usuario is None:
                return redirect(f"{reverse('login')}?next={request.path}")
            if nombre_permiso and not request.usuario.tiene_permiso(nombre_permiso):
                messages.error(request, "Tu perfil no tiene permiso para esa opción.")
                return redirect("inicio")
            return vista(request, *args, **kwargs)
        return envoltura
    return decorador


class UsuarioMiddleware:
    """En cada pedido pone request.usuario y, si DEBE_CAMBIAR_CLAVE es verdadero,
    lo manda a cambiar la clave antes de dejarlo usar el sistema."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        dni = request.session.get(CLAVE_SESION)
        request.usuario = None
        if dni:
            request.usuario = Empleado.objects.select_related("id_perfil").filter(
                dni=str(dni),
                activo="SI",
                nombre_usuario__isnull=False,
            ).first()
        if request.usuario and request.usuario.debe_cambiar_clave:
            libres = [reverse("cambiar_clave"), reverse("logout")]
            if request.path not in libres:
                return redirect("cambiar_clave")
        return self.get_response(request)


def datos_usuario(request):
    """Context processor: {{ usuario_logueado }} y {{ permisos }} en todas las plantillas."""
    u = getattr(request, "usuario", None)
    return {"usuario_logueado": u, "permisos": u.permisos() if u else set()}
