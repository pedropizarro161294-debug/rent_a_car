from django.urls import path

from . import views

urlpatterns = [
    path("inicio/", views.inicio, name="inicio"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("cambiar-clave/", views.cambiar_clave, name="cambiar_clave"),
    path("usuarios/restablecer-clave/", views.restablecer_clave, name="restablecer_clave"),
]
