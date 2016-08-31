from django.conf.urls import url
from apps.wizard.views import CreateGearView, SetGearPlugsView, CreatePlugView, CreateConnectionView

urlpatterns = [
    url(r'^gear/create/$', CreateGearView.as_view(), name='create_gear'),
    url(r'^gear/set/plugs/(?P<pk>\d+)/$', SetGearPlugsView.as_view(), name='set_gear_plugs'),
    url(r'^plug/create/(?P<plug_type>(source|target)+)/$', CreatePlugView.as_view(), name='create_plug'),
    url(r'connection/create/(?P<connector_id>\d+)/$', CreateConnectionView.as_view(), name='create_connection'),
]
