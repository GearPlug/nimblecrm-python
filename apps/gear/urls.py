from django.conf.urls import url
from apps.gear.views import CreateGearView, UpdateGearView, DeleteGearView, ListGearView

urlpatterns = [
    url(r'create/$', CreateGearView.as_view(), name='create'),
    url(r'update/(?P<pk>\d+)/$', UpdateGearView.as_view(), name='update'),
    url(r'delete/(?P<pk>\d+)/$', DeleteGearView.as_view(), name='delete'),
    url(r'list/$', ListGearView.as_view(), name='list'),
]
