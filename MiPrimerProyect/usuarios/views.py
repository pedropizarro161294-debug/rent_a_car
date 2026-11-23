from django.contrib import messages
from django.shortcuts import redirect, render

from .forms import CambiarClaveForm, LoginForm, RestablecerClaveForm
from .seguridad import CLAVE_SESION, generar_clave_temporal, permiso_requerido
from miprimerapp.models import Empleado


def login_view(request):
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        u = Empleado.objects.filter(nombre_usuario=form.cleaned_data["nombre_usuario"]).first()
        if u is None or not u.verificar_clave(form.cleaned_data["clave"]):
            messages.error(request, "Usuario o clave incorrectos.")
        elif u.activo != "SI":
            messages.error(request, "El usuario está dado de baja.")
        else:
            request.session.cycle_key()
            request.session[CLAVE_SESION] = u.dni
            if u.debe_cambiar_clave:
                messages.warning(request, "Tenés que cambiar tu clave antes de seguir.")
                return redirect("cambiar_clave")
            return redirect(request.GET.get("next") or "empleados:panel")
    return render(request, "usuarios/login.html", {"form": form})


def logout_view(request):
    request.session.flush()
    return redirect("login")


@permiso_requerido()
def inicio(request):
    return render(request, "usuarios/inicio.html")


@permiso_requerido()
def cambiar_clave(request):
    form = CambiarClaveForm(request.usuario, request.POST or None)
    if request.method == "POST" and form.is_valid():
        request.usuario.set_clave(form.cleaned_data["clave_nueva"], debe_cambiar=False)
        request.usuario.save()
        messages.success(request, "Clave actualizada.")
        return redirect("empleados:panel")
    return render(request, "usuarios/cambiar_clave.html", {"form": form})


@permiso_requerido("usuarios.restablecer_clave")
def restablecer_clave(request):
    form = RestablecerClaveForm(request.POST or None, initial={"usuario": request.GET.get("dni")})
    if request.method == "POST" and form.is_valid():
        empleado = form.cleaned_data["usuario"]
        clave = generar_clave_temporal()
        empleado.set_clave(clave, debe_cambiar=True)
        empleado.save()
        return render(
            request,
            "usuarios/clave_generada.html",
            {"u": empleado, "clave": clave, "accion": "Restablecer clave"},
        )
    return render(request, "usuarios/restablecer_clave.html", {"form": form})
