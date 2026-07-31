from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', include('clients.urls')),
    path('avances/', include('avances.urls')),
    path('personnel/', include('personnel.urls')),
    path('transentrant/', include('transentrant.urls')),
    path('produit/', include('produit.urls')),
    path('admin/', admin.site.urls),
    path('materiels/', include('materiels.urls')),
    path('materielsort/', include('materielsort.urls')),
    path('materielEntre/', include('materielEntre.urls')),
    path('depense/', include(('depense.urls', 'depense'), namespace='depense')),
    path('depot/', include(('depot.urls', 'depot'), namespace='depot')),
    path('salaire/', include(('salaire.urls', 'salaire'), namespace='salaire')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)