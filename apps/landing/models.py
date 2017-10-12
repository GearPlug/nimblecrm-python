from django.db import models
from django.utils.translation import gettext_lazy as _


class ContactModel(models.Model):
    email = models.EmailField(_('Email'), )
    name = models.CharField(_('Nombre'), max_length=254)
    text = models.TextField(_('Text'), max_length=5000)
