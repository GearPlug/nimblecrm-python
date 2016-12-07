import simplejson as json
from django import forms
from django.db import models
from django.template import defaultfilters
from django.utils.encoding import force_text
from django.utils.html import format_html
from django.utils.safestring import mark_safe


class JSONField(models.TextField):
    """
    JSONField is a generic textfield that neatly serializes/unserializes
    JSON objects seamlessly.
    Django snippet #1478

    example:
        class Page(models.Model):
            data = JSONField(blank=True, null=True)


        page = Page.objects.get(pk=5)
        page.data = {'title': 'test', 'type': 3}
        page.save()
    """

    def from_db_value(self, value, *args, **kwargs):
        if value == "":
            return None
        try:
            if isinstance(value, str):
                return json.loads(value)
        except ValueError:
            pass
        return value

    def get_db_prep_save(self, value, *args, **kwargs):
        if value == "":
            return None
        if isinstance(value, dict):
            value = json.dumps(value)
        return super(JSONField, self).get_db_prep_save(value, *args, **kwargs)
