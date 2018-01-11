from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from allauth.account.signals import user_signed_up
from apps.gp.models import Gear
from apps.billing.models import ServiceValidity, ServiceRecharge, ServiceValidityHistory
from apps.history.models import SendHistory


# TODO: ESTO NO VA AQUI
@receiver(user_signed_up)
def create_service_validity(sender, request=None, user=None, **kwargs):
    ServiceValidity.objects.create(user_id=str(user.id), current_fee_id=settings.BILLING_DEFAULT_FEE, )


@receiver(post_save, sender=ServiceRecharge)
def add_balance(sender, instance=None, **kwargs):
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


@receiver(post_save, sender=SendHistory)
def deduct_balance(sender, instance=None, created=False, **kwargs):
    if created is True:
        if instance.sent == SendHistory.SENT_STATUS.SUCCESS:
            queryset = Gear.objects.filter(pk=int(instance.gear_id)).prefetch_related('user')
            gear = queryset[0]
            print(gear)
            print(gear.user)
            service_validity = ServiceValidity.objects.get(user_id=str(gear.user.id))
            service_validity.current_balance -= service_validity.current_fee.value
            # HISTORY  #TODO: CHANGE DEFAULT OEPRATION
            history = ServiceValidityHistory(
                service_validity=service_validity,
                operation=3,
                amount=service_validity.current_fee.value,
                comment="automatic history for: consumed {}".format(service_validity.current_fee.value))

            service_validity.save(update_fields=['current_balance', ])
            history.save()
            # service_validity = instance.service_validity
            # service_validity.current_balance += instance.recharge_amount
            # service_validity.total_recharged += instance.recharge_amount
            # service_validity.save()


def create_history(service_validity_id, operation, amount=0, comment=''):
    pass
