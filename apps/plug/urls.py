from django.conf.urls import url
from apps.plug.views import CreatePlugSpecificationsView, UpdatePlugSpecificationsView, \
    PlugActionSpecificationOptionsView

from apps.plug.views import ActionListView, ActionSpecificationsListView, CreatePlugView, TestPlugView

urlpatterns = [
    url(r'create/$', CreatePlugView.as_view(), name='create'),
    url(r'create/(?P<plug_id>\d+)/specification/', CreatePlugSpecificationsView.as_view(),
        name='create_specification'),
    url(r'update/(?P<pk>\d+)/specification/$', UpdatePlugSpecificationsView.as_view(), name='update_specification'),
    url(r'action/specifications/options/$', PlugActionSpecificationOptionsView.as_view(),
        name='action_specification_options'),
    # Action list
    url(r'^action/list/$', ActionListView.as_view(), name='action_list'),
    # Action Specification list
    url(r'^action/(?P<action_id>\d+)/specification/list/$', ActionSpecificationsListView.as_view(),
        name='action_specification_list'),

]
