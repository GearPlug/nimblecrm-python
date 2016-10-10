from django import template

register = template.Library()


@register.filter('is_list')
def is_list(a):
    return isinstance(a, list)
