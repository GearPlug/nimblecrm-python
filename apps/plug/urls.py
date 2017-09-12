from django.conf.urls import url
from apps.plug.views import PlugActionSpecificationListView

from apps.plug.views import ActionListView, ActionSpecificationsListView, CreatePlugView, TestPlugView

urlpatterns = [
    url(r'create/(?P<plug_type>(source|target)+)/$', CreatePlugView.as_view(), name='create'),
    url(r'^action/list/$', ActionListView.as_view(), name='actions'),
    url(r'^action/(?P<action_id>\d+)/specification/list/$', ActionSpecificationsListView.as_view(),
        name='action_specifications'),
    url(r'actionspecifications/list/$', PlugActionSpecificationListView.as_view(),
        name='plug_action_specifications'),
    url('^test/(?P<pk>\d+)/$', TestPlugView.as_view(), name='test'),
]
