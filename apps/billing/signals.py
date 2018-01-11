from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from allauth.account.signals import user_signed_up
from apps.billing.models import ServiceValidity, ServiceRecharge, ServiceValidityHistory


# TODO: ESTO NO VA AQUI
@receiver(user_signed_up)
def create_service_validity(sender, request=None, user=None, **kwargs):
    ServiceValidity.objects.create(user_id=str(user.id), current_fee_id=settings.BILLING_DEFAULT_FEE, )


@receiver(post_save, sender=ServiceRecharge)
def add_recharge_amount_to_service_validity(sender, instance=None, **kwargs):
    # SERVICE VALIDITY
    service_validity = instance.service_validity
    service_validity.current_balance += instance.recharge_amount
    service_validity.total_recharged += instance.recharge_amount

    # HISTORY  #TODO: CHANGE DEFAULT OEPRATION
    history = ServiceValidityHistory(
        service_validity=service_validity,
        operation=1,
        amount=instance.recharge_amount,
        comment="automatic history for: RECHARGE {}".format(instance.recharge_amount))
    service_validity.save()
    history.save()
