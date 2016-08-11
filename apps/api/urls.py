from django.conf.urls import url

from apps.api import views

urlpatterns = [
    url(r'^prueba/$', views.api_prueba, name="home"),
]
