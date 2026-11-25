from django.contrib import admin

from .models import Empleado


@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    list_display = ("dni", "nombre_usuario", "apellido", "nombre", "correo", "id_perfil", "activo")
    readonly_fields = ("activo", "nombre_usuario", "clave", "fecha_ultima_modificacion", "fecha_baja")
