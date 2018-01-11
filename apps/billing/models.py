from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


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
    class OPERATION:
        RECHARGE = 1
        REVOKE = 2
        CONSUMED = 3
        BONUS_RECHARGE = 4
        REFUNDED = 5
        MODIFY_FEE = 6

    SERVICE_OPERATION = (
        (1, 'Recharge'),
        (2, 'Revoke'),
        (3, 'Consumed'),
        (4, 'Bonus recharge'),
        (5, 'Refunded'),
        (6, 'Modify Fee'),
    )
    service_validity = models.ForeignKey(ServiceValidity, on_delete=models.CASCADE,
                                         related_name='service_validity_history')
    operation = models.SmallIntegerField(_('operation'), choices=SERVICE_OPERATION, default=0)
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
