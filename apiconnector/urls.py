from django.conf import settings
from django.conf.urls import url, include
from django.conf.urls.static import static
from django.contrib import admin
from apps.gear import urls as gear_urls

urlpatterns = [
                  url(r'^admin/', admin.site.urls),
                  # url(r'^wizard/', include('apps.wizard.urls', namespace='wizard')),
                  url(r'^gear/', include(gear_urls, namespace='gear')),
                  url(r'^plug/', include('apps.plug.urls', namespace='plug')),
                  url(r'^connection/', include('apps.connection.urls', namespace='connection')),
                  url(r'^accounts/', include('allauth.urls', namespace='allauth')),
                  url(r'^', include('apps.landing.urls', namespace='landing')),
                  url(r'^', include('apps.home.urls', namespace='home')),
              ] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) \
              + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [url(r'^__debug__/', include(debug_toolbar.urls)), ] + urlpatterns
