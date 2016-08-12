from django.conf.urls import url
from apps.home.views import HomeView, DashBoardView

urlpatterns = [
    url(r'^$', HomeView.as_view(), name='homepage'),
    url(r'^dashboard/$', DashBoardView.as_view(), name='dashboard'),
]