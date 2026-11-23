from django.urls import path

from . import views, views_abm

app_name = "alquileres"

urlpatterns = [
    # Proceso de alquiler
    path("alquileres/", views.consulta, name="consulta"),
    path("alquileres/nuevo/", views.registrar, name="registrar"),
    path("alquileres/<int:pk>/", views.detalle, name="detalle"),
    path("alquileres/<int:pk>/anular/", views.anular, name="anular"),
    path("alquileres/<int:pk>/finalizar/", views.finalizar, name="finalizar"),
    path("alquileres/<int:pk>/comprobante/", views.comprobante, name="comprobante"),
    # ABM de tablas maestras
    path("clientes/", views_abm.clientes, name="clientes"),
    path("clientes/nuevo/", views_abm.cliente_alta, name="cliente_alta"),
    path("clientes/<int:pk>/editar/", views_abm.cliente_editar, name="cliente_editar"),
    path("clientes/<int:pk>/estado/", views_abm.cliente_estado, name="cliente_estado"),
    path("categorias/", views_abm.categorias, name="categorias"),
    path("categorias/nueva/", views_abm.categoria_alta, name="categoria_alta"),
    path("categorias/<int:pk>/editar/", views_abm.categoria_editar, name="categoria_editar"),
    path("categorias/<int:pk>/estado/", views_abm.categoria_estado, name="categoria_estado"),
    path("vehiculos/", views_abm.vehiculos, name="vehiculos"),
    path("vehiculos/nuevo/", views_abm.vehiculo_alta, name="vehiculo_alta"),
    path("vehiculos/<int:pk>/editar/", views_abm.vehiculo_editar, name="vehiculo_editar"),
    path("vehiculos/<int:pk>/estado/", views_abm.vehiculo_estado, name="vehiculo_estado"),
]
