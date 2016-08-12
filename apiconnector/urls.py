from django.conf import settings
from django.conf.urls import url, include
from django.conf.urls.static import static
from django.contrib import admin

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^gear/', include('apps.gear.urls', namespace='gear')),
    url(r'^plug/', include('apps.plug.urls', namespace='plug')),

    url(r'^account/', include('apps.user.urls')),
    url(r'^account/', include('account.urls')),
    url(r'^', include('apps.home.urls',  namespace='home')),
    url(r'^api/', include('apps.api.urls',  namespace='api')),
    url(r'^o/', include('oauth2_provider.urls', namespace='oauth2_provider')),

]+ static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
