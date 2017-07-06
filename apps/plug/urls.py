from django.conf.urls import url
from apps.plug.views import CreatePlugView, UpdatePlugView, DeletePlugView, ListPlugView, UpdatePlugAddActionView, \
    CreatePlugSpecificationsView, UpdatePlugSpecificationsView, GetActionsView, GetActionSpecifications

urlpatterns = [
    url(r'create/$', CreatePlugView.as_view(), name='create'),
    url(r'update/(?P<pk>\d+)/$', UpdatePlugView.as_view(), name='update'),
    url(r'update/(?P<pk>\d+)/action/', UpdatePlugAddActionView.as_view(), name='add_action'),
    url(r'delete/(?P<pk>\d+)/$', DeletePlugView.as_view(), name='delete'),
    url(r'create/(?P<plug_id>\d+)/specification/', CreatePlugSpecificationsView.as_view(),
        name='create_specification'),
    url(r'update/(?P<pk>\d+)/specification/$', UpdatePlugSpecificationsView.as_view(), name='update_specification'),
    url(r'list/$', ListPlugView.as_view(), name='list'),
    url(r'get_actions/(?P<connector_id>\d+)/(?P<action_type>(target|source)+)/$', GetActionsView.as_view(), name='get_actions'),
    url(r'get_action_specifications/(?P<action_id>\d+)/$', GetActionSpecifications.as_view(), name='get_action_specifications'),
]
