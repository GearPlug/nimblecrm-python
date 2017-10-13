from django.db import models
from django.utils.translation import gettext_lazy as _


class ContactModel(models.Model):
    email = models.EmailField(_('email'), )
    name = models.CharField(_('nombre'), max_length=254)
    text = models.TextField(_('pregunta'), max_length=5000)


class ExperienceModel(models.Model):
    name = models.CharField(_('nombre'), max_length=254)
    text = models.TextField(_('pregunta'), max_length=1000)
    image = models.ImageField(_('imagen'), upload_to='experience/image', null=True, default=None)

