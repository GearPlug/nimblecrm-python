from django.conf.urls import url
from apps.plug.views import CreatePlugView,    CreatePlugSpecificationsView, UpdatePlugSpecificationsView

urlpatterns = [
    url(r'create/$', CreatePlugView.as_view(), name='create'),
    url(r'create/(?P<plug_id>\d+)/specification/', CreatePlugSpecificationsView.as_view(),
        name='create_specification'),
    url(r'update/(?P<pk>\d+)/specification/$', UpdatePlugSpecificationsView.as_view(), name='update_specification'),
]
