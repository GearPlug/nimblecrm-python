from django.conf.urls import url
from apps.wizard.views import CreateGearView, SetGearPlugsView, CreatePlugView, CreateConnectionView, \
    UpdatePlugSetActionView, CreateGearMapView, CreatePlugSpecificationView, async_spreadsheet_info, \
    async_spreadsheet_values

urlpatterns = [
    url(r'^gear/create/$', CreateGearView.as_view(), name='create_gear'),
    url(r'^gear/list/$', CreateGearView.as_view(), name='list_gear'),
    url(r'^gear/set/plugs/(?P<pk>\d+)/$', SetGearPlugsView.as_view(), name='set_gear_plugs'),
    url(r'^plug/create/(?P<plug_type>(source|target)+)/$', CreatePlugView.as_view(), name='create_plug'),
    url(r'^plug/(?P<pk>\d+)/(?P<plug_type>(source|target)+)/set/action/$', UpdatePlugSetActionView.as_view(),
        name='plug_set_action'),
    url(r'^plug/(?P<plug_id>\d+)/set/specifications/$', CreatePlugSpecificationView.as_view(),
        name='plug_set_specifications'),
    url(r'connection/create/(?P<connector_id>\d+)/$', CreateConnectionView.as_view(), name='create_connection'),
    url(r'gear/map/(?P<gear_id>\d+)/$', CreateGearMapView.as_view(), name='create_gear_map'),

    url(r"^async/spreadsheet/info/(?P<id>.+)/$", async_spreadsheet_info, name="async_test2"),
    url(r"^async/spreadsheet/values/(?P<id>.+)/(?P<sheet_id>.+)/$", async_spreadsheet_values, name="async_test2"),
]
