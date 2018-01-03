from django.conf.urls import url
from django.views.generic import TemplateView
from apps.gear.views import CreateGearView, CreateGearGroupView, UpdateGearView, UpdateGearGroupView, DeleteGearView, \
    ListGearView, CreateGearMapView, gear_toggle, GearDownloadHistoryView, GearSendHistoryView, \
    GearFiltersView, GearActivityHistoryView, retry_send_history, set_gear_id_to_session, manual_queue


urlpatterns = [
    url(r'^create/$', CreateGearView.as_view(), name='create'),
    url(r'^sucess_create/$', TemplateView.as_view(template_name='gear/sucess_create.html'), name='sucess_create'),
    url(r'^group/create/$', CreateGearGroupView.as_view(), name='create_group'),
    url(r'^update/(?P<pk>\d+)/$', UpdateGearView.as_view(), name='update'),
    url(r'^group/update/(?P<pk>\d+)/$', UpdateGearGroupView.as_view(), name='update_group'),

    url(r'^delete/(?P<pk>\d+)/$', DeleteGearView.as_view(), name='delete'), #TODO: CHECK FUNCIONALITY.
    url(r'^list/$', ListGearView.as_view(), name='list'),

    url(r'^map/(?P<gear_id>\d+)/$', CreateGearMapView.as_view(), name='map'),
    url(r'^toggle/(?P<gear_id>\d+)/$', gear_toggle, name='toggle'),


    url(r'^download-history/(?P<pk>\d+)/$', GearDownloadHistoryView.as_view(), name='download_history'),
    url(r'^send-history/(?P<pk>\d+)/$', GearSendHistoryView.as_view(), name='send_history'),
    url(r'^recent-activity/$', GearActivityHistoryView.as_view(), name='recent_activity'),

    url(r'^filters/(?P<pk>\d+)/$', GearFiltersView.as_view(), name='filters'),
    url(r'^retry-send-history/$', retry_send_history, name='retry_send_history'),
    url(r'^set-gear-session/$', set_gear_id_to_session, name='set_gear_session'),
    url(r'^manual-queue/(?P<gear_id>\d+)/$', manual_queue, name='manual_queue'),

]
