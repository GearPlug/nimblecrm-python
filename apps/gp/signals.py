from django.dispatch import receiver
from allauth.account.signals import user_signed_up
from apps.gp.models import Profile


# TODO: ESTO NO VA AQUI
@receiver(user_signed_up)
def create_user_profile(sender, user=None, **kwargs):
    print("crear perfil para user")
    Profile.objects.create(user=user)
