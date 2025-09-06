# models.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User

@receiver(post_save, sender=User)
def crear_perfil_usuario(sender, instance, created, **kwargs):
    if created:
        from .models import Rol, Usuario
        rol_default, _ = Rol.objects.get_or_create(nombre="Cliente")
        Usuario.objects.create(user=instance, rol=rol_default)
