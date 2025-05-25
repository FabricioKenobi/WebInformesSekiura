from django.db import models
from django.contrib.auth.models import User


class Nota(models.Model):
    TIPO_CHOICES = [
        ('diario', 'diario'),
        ('mensual', 'mensual'),
    ]

    titulo = models.CharField(max_length=200)
    contenido = models.TextField()
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.titulo} ({self.tipo})"