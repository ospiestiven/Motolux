from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Usuario, Rol

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Crea un perfil de Usuario automáticamente cuando un nuevo User es creado.
    """
    if created:
        # Asigna un rol por defecto, por ejemplo 'Cliente'
        # Asegúrate de que este rol exista en tu base de datos.
        cliente_rol, _ = Rol.objects.get_or_create(nombre='Cliente')
        Usuario.objects.create(user=instance, rol=cliente_rol)