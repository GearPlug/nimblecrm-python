from django.conf import settings
from django.conf.urls import url, include
from django.conf.urls.static import static
from django.contrib import admin

urlpatterns = [
                  url(r'^admin/', admin.site.urls),
                  url(r'^wizard/', include('apps.wizard.urls', namespace='wizard')),
                  url(r'^gear/', include('apps.gear.urls', namespace='gear')),
                  url(r'^plug/', include('apps.plug.urls', namespace='plug')),
                  url(r'^connection/', include('apps.connection.urls', namespace='connection')),
                  url(r'^account/', include('apps.user.urls')),
                  url(r'^account/', include('account.urls')),
                  url(r'^', include('apps.home.urls', namespace='home')),
                  url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
                  url(r'^o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
              ] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) + static(settings.MEDIA_URL,
                                                                                           document_root=settings.MEDIA_ROOT)
if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ]
