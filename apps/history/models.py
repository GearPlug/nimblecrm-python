from django.db import models
from django.dispatch import receiver
from django.db.models.signals import post_save
from apps.billing.models import ServiceValidity, ServiceValidityHistory
from apps.gp.models import Gear


class DownloadHistory(models.Model):
    connector_id = models.CharField('connector_id', max_length=25)
    gear_id = models.CharField('gear_id', max_length=25)
    plug_id = models.CharField('plug_id', max_length=25)
    connection = models.CharField(max_length=2000)
    date = models.DateTimeField(auto_now_add=True)
    raw = models.CharField(max_length=25000)
    identifier = models.CharField('identifier', max_length=500)

    class Meta:
        db_table = "gp_downloadhistory"
        app_label = "history"


class SendHistory(models.Model):
    class SENT_STATUS:
        FAILED = 0
        SUCCESS = 1
        FILTERED = 2

    STATUS = ((0, 'Failed'),
              (1, 'Success'),
              (2, 'Filtered'),)
    connector_id = models.CharField('connector_id', max_length=25)
    gear_id = models.CharField('gear_id', max_length=25)
    plug_id = models.CharField('plug_id', max_length=25)
    connection = models.CharField(max_length=5000)
    date = models.DateTimeField(auto_now_add=True)
    data = models.CharField(max_length=25000)
    response = models.CharField(max_length=25000)
    sent = models.SmallIntegerField('sent', choices=STATUS, default=0)
    identifier = models.CharField('identifier', max_length=500)
    tries = models.IntegerField(default=1)
    version = models.CharField('version', default=1, max_length=500)

    class Meta:
        db_table = "gp_sendhistory"
        app_label = "history"


# TODO: ESTO NO VA AQUI
@receiver(post_save, sender=SendHistory)
def discount_balance(sender, instance=None, created=False, **kwargs):
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
