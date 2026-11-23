# Perfiles y permisos de acceso del sistema.
# Mismo estilo que gestion/models.py: db_table y db_column en mayúsculas.

from django.db import models


class Perfil(models.Model):
    id_perfil = models.AutoField(db_column="ID_PERFIL", primary_key=True)
    nombre_perfil = models.CharField(db_column="NOMBRE_PERFIL", max_length=50, unique=True)
    descripcion = models.CharField(db_column="DESCRIPCION", max_length=200, blank=True, null=True)

    class Meta:
        managed = True
        db_table = "perfil"
        verbose_name_plural = "perfiles"

    def __str__(self):
        return self.nombre_perfil


class Permiso(models.Model):
    id_permiso = models.AutoField(db_column="ID_PERMISO", primary_key=True)
    nombre_permiso = models.CharField(db_column="NOMBRE_PERMISO", max_length=50, unique=True)
    descripcion = models.CharField(db_column="DESCRIPCION", max_length=200, blank=True, null=True)

    class Meta:
        managed = True
        db_table = "permiso"

    def __str__(self):
        return self.nombre_permiso


class PerfilPermiso(models.Model):
    # Tabla intermedia con clave compuesta, igual que TelefonoCliente.
    pk = models.CompositePrimaryKey("id_perfil", "id_permiso")
    id_perfil = models.ForeignKey(Perfil, models.CASCADE, db_column="ID_PERFIL", related_name="perfil_permisos")
    id_permiso = models.ForeignKey(Permiso, models.CASCADE, db_column="ID_PERMISO", related_name="perfil_permisos")

    class Meta:
        managed = True
        db_table = "perfil_permiso"

    def __str__(self):
        return f"{self.id_perfil} - {self.id_permiso}"
