from django.conf.urls import url
from apps.gear.views import CreateGearView, CreateGearGroupView, UpdateGearView, UpdateGearGroupView, DeleteGearView,\
    ListGearView, CreateGearMapView, gear_toggle, DownloadHistoryView, DownloadHistoryDetailsView

urlpatterns = [
    url(r'^create/$', CreateGearView.as_view(), name='create'),
    url(r'^group/create/$', CreateGearGroupView.as_view(), name='create_group'),
    url(r'^update/(?P<pk>\d+)/$', UpdateGearView.as_view(), name='update'),
    url(r'^group/update/(?P<pk>\d+)/$', UpdateGearGroupView.as_view(), name='update_group'),

    url(r'^delete/(?P<pk>\d+)/$', DeleteGearView.as_view(), name='delete'),
    url(r'^list/$', ListGearView.as_view(), name='list'),

    url(r'^map/(?P<gear_id>\d+)/$', CreateGearMapView.as_view(), name='map'),
    url(r'^toggle/(?P<gear_id>\d+)/$', gear_toggle, name='toggle'),

    url(r'^download-history/', DownloadHistoryView.as_view(), name='download_history'),
    url(r'^download-history/(?P<identifier>\d+)/$', DownloadHistoryDetailsView.as_view(), name='download_history_details')
]
