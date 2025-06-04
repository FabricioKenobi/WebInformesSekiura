from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import CredencialesSMTP

@receiver(post_save, sender=User)
def crear_credenciales_smtp(sender, instance, created, **kwargs):
    if created:
        CredencialesSMTP.objects.create(user=instance)