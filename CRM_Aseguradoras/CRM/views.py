import csv
import json
from datetime import date, timedelta
from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.db.models.deletion import ProtectedError
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Estado,Ciudades, Departamentos, Ramos, TipoInteraccion, Formas_pago, Tipo_Poliza, Canal_venta, Tipo_DNI, Roles, Clientes, Ciudades, Productos, Canal_venta, Tipo_Poliza, Polizas, Departamentos
from django.db.models import Q, Count
from django.contrib.auth.models import User
from CRM.models import Tipo_DNI, Canal_venta, Estado




# Create your views here.
def index(request):
    return render(request, 'index.html')


def obtener_ciudades(request, departamento_id):
    ciudades = Ciudades.objects.filter(id_departamento_id=departamento_id).values("id", "descripcion")
    return JsonResponse(list(ciudades), safe=False)

def polizas_por_cliente(request, dni):
    
    try:
        # Obtener pólizas del cliente
        polizas = Polizas.objects.filter(
            dni_cliente__dni=dni
        ).select_related('id_producto')
        
        # Formatear datos para JSON
        data = []
        for poliza in polizas:
            data.append({
                'id': poliza.id,
                'producto': poliza.id_producto.descripcion,
                'fecha_inicio': poliza.fecha_inicio.strftime('%Y-%m-%d'),
                'fecha_fin': poliza.fecha_fin.strftime('%Y-%m-%d')
            })
        
        return JsonResponse(data, safe=False)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

#----------------------------#
#-----CLIENTES Y POLIZAS-----#
#----------------------------#

# Vista y lógica para mostrar y gestionar clientes y sus pólizas
def gestionar_clientes(request):

    clientes = Clientes.objects.all()
    polizas = Polizas.objects.all()
    query = request.GET.get("q")
    producto_id = request.GET.get("producto")
    estado_id = request.GET.get("estado")

    if query:
        clientes = clientes.filter(
            Q(nombre__icontains=query) | Q(dni__icontains=query)
        )

    # Obtener todas las pólizas para los clientes filtrados
    polizas = Polizas.objects.filter(dni_cliente__in=clientes).select_related("id_producto", "id_canal_venta")

    if producto_id:
        polizas = polizas.filter(id_producto_id=producto_id)

    if estado_id:
        polizas = polizas.filter(id_estado_id=estado_id)

    # Crear una estructura que contenga cada cliente con todas sus pólizas
    datos_clientes = []
    for cliente in clientes:
        polizas_cliente = polizas.filter(dni_cliente=cliente)
        datos_clientes.append({
            "cliente": cliente,
            "polizas": polizas_cliente
        })

    return render(request, "consultar.html", {
        "datos_clientes": datos_clientes,
        "query": query or "",
        "productos": Productos.objects.all(),
        "estados": Estado.objects.all(),
    })


# Mostrar en detalle la información de un cliente específico
def detalle_cliente(request, dni):


    # Buscar el cliente dentro de la misma empresa del asesor
    cliente = get_object_or_404(Clientes, dni=dni)
    poliza = Polizas.objects.filter(dni_cliente=cliente).first()
    tipos_dni = Tipo_DNI.objects.all()
    departamentos = Departamentos.objects.all()
    ciudades = Ciudades.objects.filter(id_departamento=cliente.id_ciudad.id_departamento)

    # === ACTUALIZACIÓN DE DATOS ===
    if request.method == "POST":
        cliente.celular = request.POST.get("telefono")
        cliente.telefono = request.POST.get("telefono")
        cliente.correo = request.POST.get("correo")
        cliente.direccion = request.POST.get("direccion")

        tipo_dni_id = request.POST.get("tipo_dni")
        ciudad_id = request.POST.get("ciudad")

        if tipo_dni_id:
            cliente.id_tipo_dni_id = tipo_dni_id
        if ciudad_id:
            cliente.id_ciudad_id = ciudad_id

        cliente.save()
        messages.success(request, f"Cliente '{cliente.nombre}' actualizado correctamente.")
        return redirect("detalle_cliente", dni=dni)

    context = {
        "cliente": cliente,
        "poliza": poliza,
        "tipos_dni": tipos_dni,
        "departamentos": departamentos,
        "ciudades": ciudades,
    }
    return render(request, "cliente_detalle.html", context)


# Mostrar en detalle la información de una póliza específica
def detalle_poliza(request, poliza_id):
    if not request.user.is_authenticated:
        messages.error(request, "Debes iniciar sesión.")
        return redirect("/login")

    # Buscar la póliza específica
    poliza = get_object_or_404(
        Polizas, 
        id=poliza_id
    )
    cliente = poliza.dni_cliente

    context = {
        "cliente": cliente,
        "poliza": poliza
    }
    return render(request, "poliza_detalle.html", context)

# Eliminar una póliza específica
def eliminar_poliza(request, poliza_id):

    poliza = get_object_or_404(Polizas, id=poliza_id)

    if request.method == "POST":
        poliza.id_estado = Estado.objects.get_or_create(descripcion="Cancelada")[0]
        poliza.save()
        messages.success(request, "La póliza ha sido cancelada correctamente.")
        return redirect("gestionar_clientes")

    messages.warning(request, "Operación no permitida.")
    return redirect("detalle_poliza", dni=poliza.dni_cliente.dni)

# Eliminar un cliente específico
def eliminar_cliente(request, dni):
    if not request.user.is_authenticated:
        messages.error(request, "Debes iniciar sesión.")
        return redirect("/login")


    cliente = get_object_or_404(Clientes, dni=dni)

    if request.method == "POST":
        cliente.delete()
        messages.success(request, "El cliente ha sido eliminado correctamente.")
        return redirect("gestionar_clientes")

    messages.error(request, "Operación no permitida.")
    return redirect("detalle_cliente", dni=dni)

# Crear un nuevo cliente junto con su póliza inicial
def nuevoCliente(request):
    # Datos para los selects
    tipos_dni = Tipo_DNI.objects.all()
    tipo_polizas = Tipo_Poliza.objects.all()
    productos = Productos.objects.all()
    canales = Canal_venta.objects.all()
    departamentos = Departamentos.objects.all()
    ciudades = Ciudades.objects.all()
    metodos = Formas_pago.objects.all()

    if request.method == "POST":
        nombre = request.POST.get("nombre")
        dni = request.POST.get("dni")
        tipo_dni_id = request.POST.get("tipo_dni")
        correo = request.POST.get("correo")
        telefono = request.POST.get("telefono")
        celular = request.POST.get("celular")
        direccion = request.POST.get("direccion")
        producto_id = request.POST.get("producto")
        tipo_poliza_id = request.POST.get("poliza")
        canal_id = request.POST.get("canal")
        ciudad_id = request.POST.get("ciudad")
        departamento_id = request.POST.get("metodo")
        metodo_pago_id = request.POST.get("metodo")

        # Validar duplicado
        if Clientes.objects.filter(dni=dni).exists():
            messages.warning(request, "Ya existe un cliente registrado con este DNI.")
            return redirect("/client_form/")

        # Crear cliente
        cliente = Clientes.objects.create(
            dni=dni,
            id_tipo_dni_id=tipo_dni_id,
            nombre=nombre,
            direccion=direccion or "",
            telefono=telefono or "",
            correo=correo or "",
            celular=celular or "",
            id_ciudad_id=ciudad_id
        )

        # Crear la póliza asociada al cliente y a la empresa del asesor
        Polizas.objects.create(
            id_producto_id=producto_id,
            id_canal_venta_id=canal_id,
            dni_cliente=cliente,
            id_tipo_poliza_id=tipo_poliza_id,
            id_forma_pago_id=metodo_pago_id,
            id_estado=Estado.objects.get_or_create(descripcion="Activa")[0]
        )

        messages.success(request, f"Cliente '{cliente.nombre}' y su póliza se registraron correctamente.")
        return redirect("/resumen")

    # Render de la vista con todos los datos
    return render(request, 'client_form.html', {
        "productos": productos,
        "tipos_dni": tipos_dni,
        "canales": canales,
        "departamentos": departamentos,
        "ciudades": ciudades,
        "tipos": tipo_polizas,
        "metodos": metodos
    })


# Crear poliza para usuario ya existente
def crear_poliza(request):

    clientes = Clientes.objects.all()


    # Cargar datos para los selects
    productos = Productos.objects.all()
    tipos_poliza = Tipo_Poliza.objects.all()
    canales = Canal_venta.objects.all()
    metodos = Formas_pago.objects.all()

    if request.method == "POST":
        dni_cliente_id = request.POST.get("cliente")
        producto_id = request.POST.get("producto")
        tipo_poliza_id = request.POST.get("tipo_poliza")
        canal_id = request.POST.get("canal")
        metodo_pago_id = request.POST.get("metodo")

        # Validación básica
        if not dni_cliente_id or not producto_id or not tipo_poliza_id:
            messages.error(request, "Por favor completa todos los campos obligatorios.")
            return redirect("crear_poliza")

        cliente = get_object_or_404(Clientes, dni=dni_cliente_id)


        # Crear póliza
        Polizas.objects.create(
            id_producto_id=producto_id,
            id_canal_venta_id=canal_id,
            dni_cliente=cliente,
            id_tipo_poliza_id=tipo_poliza_id,
            id_forma_pago_id=metodo_pago_id,
            id_estado=Estado.objects.get_or_create(descripcion="Activa")[0]
        )


        messages.success(request, f"La póliza para {cliente.nombre} se registró correctamente.")
        return redirect("gestionar_clientes")

    return render(request, "crear_poliza.html", {
        "titulo": "Registrar nueva póliza",
        "descripcion": "Asigna una nueva póliza a un cliente existente.",
        "clientes": clientes,
        "productos": productos,
        "tipos_poliza": tipos_poliza,
        "canales": canales,
        "metodos": metodos 
    })


#----------------------------#
#-----PANTALLA PRINCIPAL-----#
#----------------------------#
def resumen(request):

    # Filtrar solo los datos del asesor actual
    clientes_count = Clientes.objects.all().count()
    
    
    polizas_vigentes = Polizas.objects.filter(id_estado__descripcion="Activa").count()

    
    context = {

        'clientes_count': clientes_count,
        'polizas_vigentes': polizas_vigentes,

    }
    
    return render(request, 'resumen.html', context)


#----------------------------#
#------ ADMINISTRACIÓN ------#
#----------------------------#

@login_required
def panel_admin(request):


    # Contar clientes de la empresa (a través de sus asesores)
    total_clientes = Clientes.objects.all().count()

    # Contar pólizas de la empresa (a través de los clientes de la empresa)
    total_polizas = Polizas.objects.all().count()

    context = {
         'total_clientes': total_clientes,
        'total_polizas': total_polizas,

    }

    return render(request, "admin_panel.html", context)


def gestionar_datos(request):

    context = {
        "tipos_dni": Tipo_DNI.objects.all().order_by("nombre"),
        "canales": Canal_venta.objects.all().order_by("descripcion"),
        "tipos_poliza": Tipo_Poliza.objects.all().order_by("descripcion"),
        "formas_pago": Formas_pago.objects.all().order_by("descripcion"),
        "estados": Estado.objects.all().order_by("descripcion"),
        "productos": Productos.objects.all().order_by("descripcion"),
        "ciudades": Ciudades.objects.select_related('id_departamento').all().order_by("descripcion"),
        "departamentos": Departamentos.objects.all().order_by("descripcion"),
        "tipos_interaccion": TipoInteraccion.objects.all().order_by("descripcion"),
    }
    return render(request, "gestionar_datos.html", context)

def _catalog_mapping():
    return {
        "tipo_dni": (Tipo_DNI, "nombre"),
        "canal": (Canal_venta, "descripcion"),
        "tipo_poliza": (Tipo_Poliza, "descripcion"),
        "forma_pago": (Formas_pago, "descripcion"),
        "estado": (Estado, "descripcion"),
        "tipo_interaccion": (TipoInteraccion, "descripcion"),
    }

@require_POST
def crear_dato(request, recurso):
    mapping = _catalog_mapping()
    
    # Manejo especial para productos
    if recurso == "producto":
        descripcion = request.POST.get("descripcion", "").strip()
        categoria = request.POST.get("id_ramo", "").strip()

        Ramos.objects.get_or_create(descripcion=categoria)

        ramo_default = Ramos.objects.filter(descripcion__iexact=categoria).first()

        if not descripcion:
            messages.error(request, "La descripción es obligatoria.")
            return redirect(request.META.get("HTTP_REFERER", "/"))
        
        # Validar que no exista
        if Productos.objects.filter(descripcion__iexact=descripcion).exists():
            messages.warning(request, "Ya existe un producto con esa descripción.")
            return redirect(request.META.get("HTTP_REFERER", "/"))
        
        producto = Productos(
            descripcion=descripcion,
            id_ramo=ramo_default
        )
        producto.save()
        messages.success(request, "Producto creado correctamente.")
        return redirect(request.META.get("HTTP_REFERER", "/"))
    
    # Manejo especial para ciudades
    if recurso == "ciudad":
        descripcion = request.POST.get("descripcion", "").strip()
        id_departamento = request.POST.get("id_departamento", "").strip()
        
        if not descripcion or not id_departamento:
            messages.error(request, "La ciudad y el departamento son obligatorios.")
            return redirect(request.META.get("HTTP_REFERER", "/"))
        
        if Ciudades.objects.filter(descripcion__iexact=descripcion, id_departamento_id=id_departamento).exists():
            messages.warning(request, "Ya existe esa ciudad en ese departamento.")
            return redirect(request.META.get("HTTP_REFERER", "/"))
        
        try:
            departamento = Departamentos.objects.get(pk=id_departamento)
            ciudad = Ciudades(descripcion=descripcion, id_departamento=departamento)
            ciudad.save()
            messages.success(request, "Ciudad creada correctamente.")
        except Departamentos.DoesNotExist:
            messages.error(request, "El departamento seleccionado no existe.")
        return redirect(request.META.get("HTTP_REFERER", "/"))
    
    # Lógica existente para catálogos simples
    if recurso not in mapping:
        messages.error(request, "Recurso no válido.")
        return redirect(request.META.get("HTTP_REFERER", "/"))

    Model, field = mapping[recurso]
    nombre = (request.POST.get("nombre") or "").strip()
    if not nombre:
        messages.error(request, "El nombre es obligatorio.")
        return redirect(request.META.get("HTTP_REFERER", "/"))

    exists = Model.objects.filter(**{f"{field}__iexact": nombre}).exists()
    if exists:
        messages.warning(request, f"Ya existe un registro con ese nombre en {recurso.replace('_', ' ')}.")
        return redirect(request.META.get("HTTP_REFERER", "/"))

    obj = Model(**{field: nombre})
    obj.save()
    messages.success(request, "Registro creado correctamente.")
    return redirect(request.META.get("HTTP_REFERER", "/"))

@require_POST
def eliminar_dato(request, recurso, pk):
    # Manejo especial para productos
    if recurso == "producto":
        try:
            producto = Productos.objects.get(pk=pk)
            producto.delete()
            messages.success(request, "Producto eliminado correctamente.")
        except Productos.DoesNotExist:
            messages.error(request, "El producto no existe.")
        except ProtectedError:
            messages.error(request, "No se puede eliminar: está en uso por otros registros.")
        return redirect(request.META.get("HTTP_REFERER", "/"))
    
       # Lógica existente
    mapping = _catalog_mapping()
    if recurso not in mapping:
        messages.error(request, "Recurso no válido.")
        return redirect(request.META.get("HTTP_REFERER", "/"))

    Model, _ = mapping[recurso]
    try:
        obj = Model.objects.get(pk=pk)
        obj.delete()
        messages.success(request, "Registro eliminado correctamente.")
    except Model.DoesNotExist:
        messages.error(request, "El registro no existe.")
    except ProtectedError:
        messages.error(request, "No se puede eliminar: está en uso por otros registros.")
    return redirect(request.META.get("HTTP_REFERER", "/"))

