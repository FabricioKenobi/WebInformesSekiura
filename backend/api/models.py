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
    
class mail(models.Model):
    ASUNTO_CHOICES = [
        ('reunion', 'Reunión'),
        ('informe', 'Informe'),
        ('recordatorio', 'Recordatorio'),
    ]

    asunto = models.CharField(max_length=100, choices=ASUNTO_CHOICES)
    fecha_evento = models.DateField()
    cuerpo = models.TextField()
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    enviado = models.BooleanField(default=False)  # opcional, si querés trackearlo
    fecha_creacion = models.DateTimeField(auto_now_add=True)

class Cliente(models.Model):
    nombre = models.CharField(max_length=100)
    email_1 = models.EmailField(null=True, blank=True)
    email_2 = models.EmailField(null=True, blank=True)
    email_3 = models.EmailField(null=True, blank=True)
    email_4 = models.EmailField(null=True, blank=True)
    email_5 = models.EmailField(null=True, blank=True)
    email_6 = models.EmailField(null=True, blank=True)
    cc_1 = models.EmailField(null=True, blank=True)
    cc_2 = models.EmailField(null=True, blank=True)

    def lista_emails(self):
        emails = [getattr(self, f"email_{i}") for i in range(1, 7) if getattr(self, f"email_{i}")]
        cc = [self.cc_1, self.cc_2]
        cc = [c for c in cc if c]
        return ", ".join(emails + [f"CC: {c}" for c in cc])

    def __str__(self):
        return self.nombre
    
class PlantillaEmail(models.Model):
    tipo = models.CharField(max_length=50)  # Ej: 'recordatorio', 'reunión'
    asunto = models.CharField(max_length=100)
    cuerpo_base = models.TextField()  # Podés usar {fecha} como placeholder

    def __str__(self):
        return self.tipo
    
class EmailEnviado(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    plantilla = models.ForeignKey(PlantillaEmail, on_delete=models.SET_NULL, null=True)
    fecha_evento = models.DateField()
    asunto = models.CharField(max_length=100)
    cuerpo = models.TextField()
    enviado = models.BooleanField(default=False)
    fecha_envio = models.DateTimeField(auto_now_add=True)
