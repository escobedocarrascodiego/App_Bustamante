from django.db import models


class Noticia(models.Model):
    titulo = models.CharField(max_length=200)
    resumen = models.CharField(max_length=300, blank=True)
    contenido = models.TextField()
    imagen = models.ImageField(upload_to="noticias/", blank=True, null=True)
    url_fuente = models.URLField(blank=True)
    publicada = models.BooleanField(default=True)
    fecha_publicacion = models.DateTimeField(auto_now_add=True)
    destacada = models.BooleanField(default=False)

    class Meta:
        ordering = ["-fecha_publicacion"]
        verbose_name = "Noticia"
        verbose_name_plural = "Noticias"

    def __str__(self):
        return self.titulo


class LugarInteres(models.Model):
    TIPOS = [
        ("PARQUE", "Parque"),
        ("BIBLIOTECA", "Biblioteca"),
        ("CENTRO_SALUD", "Centro de salud"),
        ("SERENAZGO", "Serenazgo"),
        ("COMPLEJO", "Complejo deportivo"),
        ("CASA_CULTURAL", "Casa cultural"),
        ("OTRO", "Otro"),
    ]

    nombre = models.CharField(max_length=150)
    tipo = models.CharField(max_length=20, choices=TIPOS, default="OTRO")
    direccion = models.CharField(max_length=200, blank=True)
    latitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    horario = models.CharField(max_length=120, blank=True)
    descripcion = models.TextField(blank=True)
    imagen = models.ImageField(upload_to="lugares/", blank=True, null=True)

    class Meta:
        ordering = ["tipo", "nombre"]
        verbose_name = "Lugar de interes"
        verbose_name_plural = "Lugares de interes"

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.nombre}"


class Contacto(models.Model):
    area = models.CharField(max_length=120)
    responsable = models.CharField(max_length=120, blank=True)
    telefono = models.CharField(max_length=50, blank=True)
    whatsapp = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    horario = models.CharField(max_length=120, blank=True)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["orden", "area"]
        verbose_name = "Contacto"
        verbose_name_plural = "Contactos"

    def __str__(self):
        return self.area
