from django.db import models
from django.contrib.auth.models import User


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
    IPSIEM = models.CharField(max_length=200, null=True, blank=True)
    FQDN = models.CharField(max_length=200, null=True, blank=True)
    diario = models.CharField(max_length=200, null=True, blank=True)
    semanal = models.CharField(max_length=200, null=True, blank=True)
    mensual = models.CharField(max_length=200, null=True, blank=True)

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
    fecha_evento = models.DateField(null=True, blank=True)
    asunto = models.CharField(max_length=100)
    cuerpo = models.TextField()
    enviado = models.BooleanField(default=False)
    fecha_envio = models.DateTimeField(auto_now_add=True)
    archivo_adjunto = models.FileField(upload_to='adjuntos/', null=True, blank=True)

class CredencialesSMTP(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='credenciales_smtp')
    smtp_host = models.CharField(max_length=255)
    smtp_puerto = models.IntegerField(default=465)
    
    smtp_user = models.EmailField()
    smtp_password = models.CharField(max_length=255)
    email_remitente = models.EmailField()
    imagen = models.ImageField(upload_to='firmas/', null=True, blank=True)