from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model
from django.core.exceptions import MultipleObjectsReturned

class SocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Si existe un usuario con el mismo email, conecta la social account a ese usuario
    evitando que allauth muestre el formulario de signup.
    """
    def pre_social_login(self, request, sociallogin):
        # si ya está autenticado, no hacemos nada
        if request.user.is_authenticated:
            return

        email = getattr(sociallogin.user, "email", None)
        if not email:
            return

        User = get_user_model()
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return
        except MultipleObjectsReturned:
            return

        # si la social account ya está vinculada, no hacer nada
        if sociallogin.is_existing:
            return

        # Conectar la social account al usuario existente
        try:
            sociallogin.connect(request, user)
        except Exception:
            # si falla la conexión, simplemente no hacer la conexión automática
            return