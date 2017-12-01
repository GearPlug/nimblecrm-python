from django.conf.urls import url
from apps.gear.views import CreateGearView, CreateGearGroupView, UpdateGearView, UpdateGearGroupView, DeleteGearView, \
    ListGearView, CreateGearMapView, gear_toggle, ActivityView, GearDownloadHistoryView, GearSendHistoryView, \
    GearFiltersView, GearActivitiesHistoryView, retry_send_history, set_gear_id_to_session


urlpatterns = [
    url(r'^create/$', CreateGearView.as_view(), name='create'),
    url(r'^group/create/$', CreateGearGroupView.as_view(), name='create_group'),
    url(r'^update/(?P<pk>\d+)/$', UpdateGearView.as_view(), name='update'),
    url(r'^group/update/(?P<pk>\d+)/$', UpdateGearGroupView.as_view(), name='update_group'),

    url(r'^delete/(?P<pk>\d+)/$', DeleteGearView.as_view(), name='delete'),
    url(r'^list/$', ListGearView.as_view(), name='list'),

    url(r'^map/(?P<gear_id>\d+)/$', CreateGearMapView.as_view(), name='map'),
    url(r'^toggle/(?P<gear_id>\d+)/$', gear_toggle, name='toggle'),

    url(r'^activity/$', ActivityView.as_view(), name='activity'),

    url(r'^download-history/(?P<pk>\d+)/$', GearDownloadHistoryView.as_view(), name='download_history'),
    url(r'^send-history/(?P<pk>\d+)/$', GearSendHistoryView.as_view(), name='send_history'),
    url(r'^activities-history/$', GearActivitiesHistoryView.as_view(), name='activities_history'),

    url(r'^filters/(?P<pk>\d+)/$', GearFiltersView.as_view(), name='filters'),
    url(r'^retry-send-history/$', retry_send_history, name='retry_send_history'),
    url(r'^set-gear-session/$', set_gear_id_to_session, name='set_gear_session'),
]
