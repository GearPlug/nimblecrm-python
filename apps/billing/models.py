from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.dispatch import receiver
from django.db.models.signals import post_save
from allauth.account.signals import user_signed_up, user_logged_in


class ServiceFee(models.Model):
    name = models.CharField(_(''), max_length=50)
    value = models.DecimalField(_('recharge amount'), decimal_places=4, max_digits=5)


class ServiceValidity(models.Model):
    user_id = models.CharField(_('user'), max_length=12)
    total_recharged = models.DecimalField(_('recharge amount'), decimal_places=4, max_digits=11, default=0)
    current_balance = models.DecimalField(_('current balance'), decimal_places=4, max_digits=10, default=0)
    last_modified = models.DateTimeField(_('last modified'), auto_now=True)
    created = models.DateTimeField(_('created'), auto_now_add=True)
    current_fee = models.ForeignKey(ServiceFee, related_name='service_validity')

    @property
    def is_active(self):
        if self.ends_at is not None:
            return timezone.now() < self.ends_at
        return False


class ServiceValidityHistory(models.Model):
    OPERATION = (
        (1, 'Recharge'),
        (2, 'Revoke'),
        (3, 'Consumed'),
        (4, 'Bonus recharge'),
        (5, 'Refunded'),
        (6, 'Modify Fee'),
    )
    service_validity = models.ForeignKey(ServiceValidity, on_delete=models.CASCADE,
                                         related_name='service_validity_history')
    operation = models.SmallIntegerField(_('operation'), choices=OPERATION, default=0)
    amount = models.DecimalField(_('amount'), decimal_places=4, max_digits=10)
    comment = models.CharField(_('operation'), max_length=150)
    created = models.DateTimeField(_('created'), auto_now_add=True)


class ServiceRecharge(models.Model):
    service_validity = models.ForeignKey(ServiceValidity, on_delete=models.CASCADE, related_name='service_recharge')
    recharge_amount = models.DecimalField(_('recharge amount'), decimal_places=4, max_digits=10)
    created = models.DateTimeField(_('created'), auto_now_add=True)
    expiration_date = models.DateTimeField(_('expiration date'))


class Invoice(models.Model):
    service_recharge = models.OneToOneField(ServiceRecharge)


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
