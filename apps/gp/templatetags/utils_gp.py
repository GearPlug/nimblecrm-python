from django import template

register = template.Library()


@register.filter('is_list')
def is_list(a):
    return isinstance(a, list)


@register.filter('is_tuple')
def is_tuple(a):
    return isinstance(a, tuple)
