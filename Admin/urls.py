
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .views import welcome
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', welcome),
    path('api/v1/', include('main.urls'))
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
