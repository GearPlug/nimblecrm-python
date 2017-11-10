from django.db import models


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
    SENT = (
        (0, 'Failed'),
        (1, 'Sent'),
        (2, 'Filtered'),
    )
    connector_id = models.CharField('connector_id', max_length=25)
    gear_id = models.CharField('gear_id', max_length=25)
    plug_id = models.CharField('plug_id', max_length=25)
    connection = models.CharField(max_length=5000)
    date = models.DateTimeField(auto_now_add=True)
    data = models.CharField(max_length=25000)
    response = models.CharField(max_length=25000)
    sent = models.SmallIntegerField('sent', choices=SENT, default=0)
    identifier = models.CharField('identifier', max_length=500)
    tries = models.IntegerField(default=1)

    class Meta:
        db_table = "gp_sendhistory"
        app_label = "history"
