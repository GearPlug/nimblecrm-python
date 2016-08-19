from django.conf.urls import url
from apps.plug.views import CreatePlugView, UpdatePlugView, DeletePlugView, ListPlugView, UpdatePlugAddActionView, \
    CreatePlugSpecificationsView

urlpatterns = [
    url(r'create/$', CreatePlugView.as_view(), name='create'),
    url(r'update/(?P<pk>\d+)/$', UpdatePlugView.as_view(), name='update'),
    url(r'update/(?P<pk>\d+)/action/', UpdatePlugAddActionView.as_view(), name='add_action'),
    url(r'delete/(?P<pk>\d+)/$', DeletePlugView.as_view(), name='delete'),
    url(r'create/(?P<plug_id>\d+)/specifications/', CreatePlugSpecificationsView.as_view(), name='create_specification'),
    url(r'list/$', ListPlugView.as_view(), name='list'),
]
