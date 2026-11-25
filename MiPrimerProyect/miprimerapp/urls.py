from django.urls import path

from . import views

app_name = "empleados"

urlpatterns = [
    path("", views.panel_empleados, name="panel"),
    path("empleados/", views.panel_empleados, name="listado"),
    path("empleados/alta/", views.alta_empleado, name="alta"),
    path("empleados/<int:empleado_id>/editar/", views.editar_empleado, name="editar"),
    path("empleados/bajas/", views.baja_empleados, name="bajas"),
    path("empleados/<int:empleado_id>/baja/", views.dar_de_baja_empleado, name="baja"),
    path("empleados/<int:empleado_id>/reactivar/", views.reactivar_empleado, name="reactivar"),
]