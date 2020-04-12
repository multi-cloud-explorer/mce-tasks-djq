import re

from django.contrib import admin
from django.urls import path, include
from django.views.generic.base import RedirectView
from django.contrib.staticfiles.views import serve
from django.urls import re_path
from django.conf import settings

def _serve(request, path, insecure=False, **kwargs):
    return serve(request, path, insecure=True, show_indexes=True, **kwargs)

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='admin:index', permanent=True)),
    path('adminmce/', admin.site.urls),
    path('select2/', include('django_select2.urls')),
    re_path(r'^%s(?P<path>.*)$' % re.escape(settings.STATIC_URL.lstrip('/')), _serve),
]

