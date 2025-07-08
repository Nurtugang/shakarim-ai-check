from django.contrib import admin
from django.urls import include, path
from django.views.i18n import set_language

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", include("index.urls")),
    path("", include("ai_check.urls")),
    path('set_language/', set_language, name='set_language'),
]
