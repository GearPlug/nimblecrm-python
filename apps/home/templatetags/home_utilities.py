from django import template

register = template.Library()


@register.simple_tag()
def get_active_nav_item(request, view_name):
    from django.core.urlresolvers import resolve, Resolver404
    if not request:
        return ''
    try:
        return 'active' if resolve(request.path_info).url_name == view_name else ''
    except Resolver404:
        return ''


@register.simple_tag()
def has_related_object(list, obj):
    for item in list:
        if hasattr(item, obj):
            return True
    return False
