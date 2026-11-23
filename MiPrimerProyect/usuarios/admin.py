from django.contrib import admin

from .models import Perfil, Permiso

# PerfilPermiso no se registra: igual que TelefonoCliente, tiene clave compuesta.
admin.site.register(Perfil)
admin.site.register(Permiso)
