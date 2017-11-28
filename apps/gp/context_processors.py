from apps.gp.models import Gear


def progress(request):
    """
    This is sparta.
    """
    context_extras = {'progress': None}
    print(request.resolver_match.view_name)
    gear = Gear.objects.get(id=request.session['gear_id'])
    print(gear)
    view_name = request.resolver_match.view_name
    if view_name == 'gear:update':
        context_extras['progress'] = 1
    if view_name == 'connection:connector_list' or view_name == 'connection:list' or view_name == 'connection:create' or view_name == 'plug:create':
        if not gear.source:
            context_extras['progress'] = 2
        else:
            context_extras['progress'] = 4
    if view_name == 'plug:test':
        if not gear.source:
            context_extras['progress'] = 3
        else:
            context_extras['progress'] = 5
    if view_name == 'gear:map':
        context_extras['progress'] = 6
    return context_extras
