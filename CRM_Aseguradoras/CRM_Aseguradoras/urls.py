import CRM.views
from django.contrib import admin
from django.urls import path

urlpatterns = [
    path('admin/', admin.site.urls),
    path("panel_admin/", CRM.views.panel_admin, name="admin_panel"),
    path('', CRM.views.index),
    path('gestionar/', CRM.views.gestionar_clientes, name='gestionar_clientes'),
    path('resumen/', CRM.views.resumen, name='panel_resumen'),
    path('client_form/', CRM.views.nuevoCliente),
    path('clientes/<str:dni>/', CRM.views.detalle_cliente, name='detalle_cliente'),
    path('poliza/<str:poliza_id>/', CRM.views.detalle_poliza, name='detalle_poliza'),
    path('poliza/<str:poliza_id>/eliminar', CRM.views.eliminar_poliza, name='eliminar_poliza'),
    path('clientes/<str:dni>/eliminar/', CRM.views.eliminar_cliente, name='eliminar_cliente'),
    path('gestionar/crear/', CRM.views.crear_poliza, name='crear_poliza'),
    path("api/polizas-cliente/<str:dni>/", CRM.views.polizas_por_cliente, name="polizas_por_cliente"),
    path('polizas-cliente/<str:dni>/', CRM.views.polizas_por_cliente, name='polizas_por_cliente'),
    path('upload/', CRM.views.upload_file, name='upload_file'),

    path("datos/", CRM.views.gestionar_datos, name="gestionar_datos"),
    path("datos/crear/<str:recurso>/", CRM.views.crear_dato, name="crear_dato"),
    path("datos/eliminar/<str:recurso>/<int:pk>/", CRM.views.eliminar_dato, name="eliminar_dato"),


]
