import csv
import json
from datetime import date, timedelta
from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.db.models.deletion import ProtectedError
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
import pandas as pd
from django.core.paginator import Paginator

from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Estado,Ciudades, Ramos, TipoInteraccion, Formas_pago, Tipo_Poliza, Canal_venta, Tipo_DNI, Roles, Clientes, Ciudades, Productos, Canal_venta, Tipo_Poliza, Polizas
from django.db.models import Q, Count
from django.contrib.auth.models import User
from CRM.models import Tipo_DNI, Canal_venta, Estado




# Create your views here.
def index(request):
    return render(request, 'index.html')

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

    query = request.GET.get("q")
    producto_id = request.GET.get("producto")
    estado_id = request.GET.get("estado")

    # Comenzar desde las pólizas (más eficiente para paginación)
    polizas = Polizas.objects.select_related("id_producto", "id_canal_venta", "dni_cliente", "id_estado").all()

    # Búsqueda: nombre o dni del cliente O id de póliza
    if query:
        q = str(query).strip()
        polizas = polizas.filter(
            Q(dni_cliente__nombre__icontains=q) |
            Q(dni_cliente__dni__icontains=q) |
            Q(id__icontains=q)
        )

    # Filtros adicionales sobre pólizas
    if producto_id:
        polizas = polizas.filter(id_producto_id=producto_id)

    if estado_id:
        polizas = polizas.filter(id_estado_id=estado_id)

    # Paginación
    page_number = request.GET.get("page", 1)
    paginator = Paginator(polizas, 10)  # 10 por página (ajusta)
    page_obj = paginator.get_page(page_number)

    # Agrupar solo las pólizas de la página actual por cliente (preserva objetos relacionados)
    datos_clientes = []
    seen = set()
    for pol in page_obj.object_list:
        dni_cliente = pol.dni_cliente.dni
        if dni_cliente in seen:
            continue
        seen.add(dni_cliente)
        polizas_cliente = [p for p in page_obj.object_list if p.dni_cliente.dni == dni_cliente]
        datos_clientes.append({
            "cliente": pol.dni_cliente,
            "polizas": polizas_cliente
        })

    return render(request, "consultar.html", {
        "datos_clientes": datos_clientes,
        "page_obj": page_obj,
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
    ciudades = Ciudades.objects.all()

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
    tipos_dni = Tipo_DNI.objects.all().order_by("nombre")
    tipo_polizas = Tipo_Poliza.objects.all().order_by("descripcion")
    productos = Productos.objects.all().order_by("descripcion")
    canales = Canal_venta.objects.all().order_by("descripcion")
    ciudades = Ciudades.objects.all().order_by("descripcion")

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
        numero_poliza = request.POST.get("numero")


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
            id=numero_poliza,
            id_producto_id=producto_id,
            id_canal_venta_id=canal_id,
            dni_cliente=cliente,
            id_tipo_poliza_id=tipo_poliza_id,
            id_estado=Estado.objects.get_or_create(descripcion="Activa")[0]
            
        )

        messages.success(request, f"Cliente '{cliente.nombre}' y su póliza se registraron correctamente.")
        return redirect("/resumen")

    # Render de la vista con todos los datos
    return render(request, 'client_form.html', {
        "productos": productos,
        "tipos_dni": tipos_dni,
        "canales": canales,
        "ciudades": ciudades,
        "tipos": tipo_polizas,
    })


# Crear poliza para usuario ya existente
def crear_poliza(request):

    clientes = Clientes.objects.all().order_by("nombre")


    # Cargar datos para los selects
    productos = Productos.objects.all().order_by("descripcion")
    tipos_poliza = Tipo_Poliza.objects.all().order_by("descripcion")
    canales = Canal_venta.objects.all().order_by("descripcion")

    if request.method == "POST":
        dni_cliente_id = request.POST.get("cliente")
        producto_id = request.POST.get("producto")
        tipo_poliza_id = request.POST.get("tipo_poliza")
        canal_id = request.POST.get("canal")
        numero_poliza = request.POST.get("numero")

        # Validación básica
        if not dni_cliente_id or not producto_id or not tipo_poliza_id:
            messages.error(request, "Por favor completa todos los campos obligatorios.")
            return redirect("crear_poliza")

        cliente = get_object_or_404(Clientes, dni=dni_cliente_id)


        # Crear póliza
        Polizas.objects.create(
            id=numero_poliza,
            id_producto_id=producto_id,
            id_canal_venta_id=canal_id,
            dni_cliente=cliente,
            id_tipo_poliza_id=tipo_poliza_id,
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
        "ciudades": Ciudades.objects.all().order_by("descripcion"),
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
        
        if not descripcion:
            messages.error(request, "La descripción de la ciudad es obligatoria.")
            return redirect(request.META.get("HTTP_REFERER", "/"))
        
        if Ciudades.objects.filter(descripcion__iexact=descripcion).exists():
            messages.warning(request, "Ya existe esa ciudad.")
            return redirect(request.META.get("HTTP_REFERER", "/"))
        
        ciudad = Ciudades(descripcion=descripcion)
        ciudad.save()
        messages.success(request, "Ciudad creada correctamente.")
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

@login_required
def upload_file(request):
    if request.method == 'POST' and request.FILES.get('data_file'):
        archivo = request.FILES['data_file']
        
        try:
            # Leer el archivo CSV o XLSX
            if archivo.name.endswith('.csv'):
                df = pd.read_csv(archivo, header=0)
            elif archivo.name.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(archivo, header=0)
            else:
                messages.error(request, "Formato no válido. Usa CSV o XLSX.")
                return redirect('upload_file')
            
            # Procesar el archivo
            resultado = procesar_datos(df)
            messages.success(request, resultado['mensaje'])
            return redirect('upload_file')
            
        except Exception as e:
            messages.error(request, f"Error al procesar el archivo: {str(e)}")
            return redirect('upload_file')
    
    return render(request, 'upload.html')


def procesar_datos(df):

    clientes_creados = 0
    clientes_actualizados = 0
    polizas_creadas = 0
    errores = 0

    for index, row in df.iterrows():
        try:
            # ======================
            # CIUDAD (crear si no existe)
            # ======================
            ciudad = None
            # Soportar encabezados 'CIUDAD' o 'Ciudad'
            ciudad_val = row.get('CIUDAD') or row.get('Ciudad')
            if pd.notna(ciudad_val):
                ciudad_desc = str(ciudad_val).strip()
                ciudad = Ciudades.objects.filter(descripcion__iexact=ciudad_desc).first()
                if not ciudad:
                    ciudad = Ciudades.objects.create(descripcion=ciudad_desc)

            # Si no viene ciudad, intentar asignar la primera existente (prevención)
            if not ciudad:
                ciudad = Ciudades.objects.first()

            # ======================
            # TIPO DNI (crear si no existe)
            # ======================
            tipo_dni = None
            if pd.notna(row.get('Tipo Dni Tomador')):
                tipo_dni_desc = str(row['Tipo Dni Tomador']).strip()
                tipo_dni = Tipo_DNI.objects.filter(nombre__iexact=tipo_dni_desc).first()
                if not tipo_dni:
                    tipo_dni = Tipo_DNI.objects.create(nombre=tipo_dni_desc)
            if not tipo_dni:
                tipo_dni = Tipo_DNI.objects.first()

            # ======================
            # CLIENTE (get_or_create / actualizar)
            # ======================
            dni = str(row.get('N° Dni Tomador') or "").strip()
            if not dni:
                raise ValueError("DNI vacío")

            cliente, creado = Clientes.objects.get_or_create(
                dni=dni,
                defaults={
                    'nombre': str(row.get('Nombre Tomador') or "").strip(),
                    'direccion': str(row.get('Dirección Tomador', '')).strip() or "Sin Registrar",
                    'telefono': str(row.get('Teléfono Fijo Tomador', '')).strip() or "Sin Registrar",
                    'celular': str(row.get('Teléfono Celular Tomador', '')).strip() or "Sin Registrar",
                    'id_tipo_dni': tipo_dni,
                    'id_ciudad': ciudad
                }
            )

            if creado:
                clientes_creados += 1
            else:
                cliente.nombre = str(row.get('Nombre Tomador') or "").strip()
                cliente.direccion = str(row.get('Dirección Tomador', '')).strip() or "Sin Registrar"
                cliente.telefono = str(row.get('Teléfono Fijo Tomador', '')).strip() or "Sin Registrar"
                cliente.celular = str(row.get('Teléfono Celular Tomador', '')).strip() or "Sin Registrar"
                cliente.id_tipo_dni = tipo_dni
                cliente.id_ciudad = ciudad
                cliente.save()
                clientes_actualizados += 1

            # ======================
            # PRODUCTO (crear si no existe)
            # ======================
            producto = None
            if pd.notna(row.get('Producto')):
                producto_desc = str(row['Producto']).strip()
                producto = Productos.objects.filter(descripcion__iexact=producto_desc).first()
                if not producto:
                    ramo_def = Ramos.objects.first()
                    producto = Productos.objects.create(descripcion=producto_desc, id_ramo=ramo_def)
            if not producto:
                producto = Productos.objects.first()

            # ======================
            # CANAL DE VENTA (crear si no existe)
            # ======================
            canal = None
            if pd.notna(row.get('Canal Ventas')):
                canal_desc = str(row['Canal Ventas']).strip()
                canal = Canal_venta.objects.filter(descripcion__iexact=canal_desc).first()
                if not canal:
                    canal = Canal_venta.objects.create(descripcion=canal_desc)
            if not canal:
                canal = Canal_venta.objects.first()

            # ======================
            # TIPO DE PÓLIZA / FORMA PAGO (crear si no existe)
            # Nota: el archivo usa 'Forma Pago' y en este código se busca en Tipo_Poliza.
            # Si tu intención es usar Formas_pago cambia Tipo_Poliza por Formas_pago aquí.
            # ======================
            forma_pago = None
            if pd.notna(row.get('Forma Pago')):
                forma_desc = str(row['Forma Pago']).strip()
                # Mantengo Tipo_Poliza como en la versión original; ajustar si corresponde.
                forma_pago = Tipo_Poliza.objects.filter(descripcion__iexact=forma_desc).first()
                if not forma_pago:
                    forma_pago = Tipo_Poliza.objects.create(descripcion=forma_desc)
            if not forma_pago:
                forma_pago = Tipo_Poliza.objects.first()

            # ======================
            # CREAR PÓLIZA si existe ID Póliza
            # ======================
            if pd.notna(row.get('Póliza')):
                id_poliza = str(row['Póliza']).strip()
                if id_poliza and not Polizas.objects.filter(id=id_poliza).exists():
                    estado = Estado.objects.filter(descripcion__iexact="Activa").first() or Estado.objects.first()

                    Polizas.objects.create(
                        id=id_poliza,
                        dni_cliente=cliente,
                        id_producto=producto,
                        id_canal_venta=canal,
                        id_tipo_poliza=forma_pago,
                        id_estado=estado,
                    )
                    polizas_creadas += 1

        except Exception as e:
            errores += 1
            print(f"Error en fila {index + 1}: {str(e)}")

    mensaje = f"Importación completada: {clientes_creados} clientes creados, {clientes_actualizados} clientes actualizados, {polizas_creadas} pólizas creadas, {errores} errores."
    return {'exito': True, 'mensaje': mensaje}