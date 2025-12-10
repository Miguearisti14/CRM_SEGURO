from django.contrib import admin
from .models import (
    Roles, Tipo_DNI, TipoInteraccion, Estado, Ramos,
    Tipo_Poliza, Canal_venta, Formas_pago,
    Ciudades, Productos, Clientes,Polizas
)

admin.site.register(Roles)
admin.site.register(Tipo_DNI)
admin.site.register(TipoInteraccion)
admin.site.register(Estado)
admin.site.register(Ramos)
admin.site.register(Tipo_Poliza)
admin.site.register(Canal_venta)
admin.site.register(Formas_pago)
admin.site.register(Ciudades)
admin.site.register(Productos)
admin.site.register(Clientes)
admin.site.register(Polizas)
