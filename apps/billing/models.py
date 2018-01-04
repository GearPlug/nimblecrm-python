from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class ServiceFee(models.Model):
    name = models.CharField(_(''), max_length=50)
    value = models.DecimalField(_('recharge amount'), decimal_places=4, max_digits=5)


class ServiceValidity(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='service_validity')
    total_recharged = models.DecimalField(_('recharge amount'), decimal_places=4, max_digits=11)
    current_balance = models.DecimalField(_('current balance'), decimal_places=4, max_digits=10)
    last_modified = models.DateTimeField(_('last modified'), auto_now=True)
    created = models.DateTimeField(_('created'), auto_now_add=True)
    current_fee = models.ForeignKey(ServiceFee, related_name='fee_service_validity')

    @property
    def is_active(self):
        if self.ends_at is not None:
            return timezone.now() < self.ends_at
        return False


class ServiceValidityHistory(models.Model):
    OPERATION = (
        ('1', 'Recharge'),
        ('2', 'Revoke'),
        ('3', 'Consumed'),
        ('4', 'Bonus recharge'),
        ('5', 'Refunded'),
    )
    service_validity = models.ForeignKey(ServiceValidity, on_delete=models.CASCADE,
                                         related_name='service_validity_history')
    operation = models.CharField(_('operation'), choices=OPERATION, max_length=3)
    amount = models.DecimalField(_('amount'), decimal_places=4, max_digits=10)


class ServiceRecharge(models.Model):
    service_validity = models.ForeignKey(ServiceValidity, on_delete=models.CASCADE, related_name='service_recharge')
    recharge_amount = models.DecimalField(_('recharge amount'), decimal_places=4, max_digits=10)
    created = models.DateTimeField(_('created'), auto_now_add=True)
    expiration_date = models.DateTimeField(_('expiration date'))


class Invoice(models.Model):
    service_recharge = models.OneToOneField(ServiceRecharge)
