from django.conf.urls import url
from apps.plug.views import PlugActionSpecificationOptionsView

from apps.plug.views import ActionListView, ActionSpecificationsListView, CreatePlugView, TestPlugView

urlpatterns = [
    url(r'create/$', CreatePlugView.as_view(), name='create'),
    url(r'action/specifications/options/$', PlugActionSpecificationOptionsView.as_view(),
        name='action_specification_options'),
    # Action list
    url(r'^action/list/$', ActionListView.as_view(), name='action_list'),
    # Action Specification list
    url(r'^action/(?P<action_id>\d+)/specification/list/$', ActionSpecificationsListView.as_view(),
        name='action_specification_list'),

]
