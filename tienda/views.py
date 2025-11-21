from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.conf import settings
import json
from decimal import Decimal
from django.db import transaction

from .models import Producto, Rol, Categoria, Usuario, Pedido, CarritoProductoPedido, Transaccion, ProductoImagen
from .forms import ProductoForm, categoriaForm, UsuarioForm, ProductoImagenForm
from .utils import generate_payment_signature, generate_confirmation_signature  # ✅ importamos desde utils


# --------------------------
# VISTAS PAYU
# --------------------------

@login_required
def payu_checkout(request, pedido_id):
    """
    Genera el formulario para PayU WebCheckout (modo sandbox).
    """
    pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user.perfil)

    # 1. Creamos una descripción detallada con los nombres de los productos
    nombres_productos = ", ".join([item.producto.nombre for item in pedido.carritos.all()])
    descripcion_pago = f"Compra en Motolux: {nombres_productos}"

    
    reference_code = f"MOTO-{pedido.id}"

    
    # PayU es muy estricto con el formato del monto.
    # Para COP, PayU espera dos decimales. Forzamos este formato.
    amount = "{:.2f}".format(Decimal(pedido.total))
    currency = settings.PAYU_CURRENCY

    signature = generate_payment_signature(
        settings.PAYU_API_KEY,
        settings.PAYU_MERCHANT_ID,
        reference_code,
        amount,
        currency,
        secret_key=getattr(settings, "PAYU_SECRET_KEY", None)
    )

    action_url = settings.PAYU_SANDBOX_URL if settings.PAYU_USE_SANDBOX else settings.PAYU_PROD_URL

    form_html = f"""
    <html><body>
      <h3>Redirigiendo a PayU (PRUEBAS)…</h3>
      <form id="payuForm" method="post" action="{action_url}">
        <input name="merchantId" type="hidden" value="{settings.PAYU_MERCHANT_ID}" />
        <input name="accountId" type="hidden" value="{settings.PAYU_ACCOUNT_ID}" />
        <input name="description" type="hidden" value="{descripcion_pago}" />
        <input name="referenceCode" type="hidden" value="{reference_code}" />
        <input name="amount" type="hidden" value="{amount}" />
        <input name="currency" type="hidden" value="{currency}" />
        <input name="signature" type="hidden" value="{signature}" />
        <input name="test" type="hidden" value="1" />
        <!-- 2. Añadimos el nombre completo del comprador -->
        <input name="buyerFullName" type="hidden" value="{request.user.get_full_name()}" />
        <input name="buyerEmail" type="hidden" value="{request.user.email}" />
        <input name="responseUrl" type="hidden" value="{settings.PAYU_RESPONSE_URL}" />
        <input name="confirmationUrl" type="hidden" value="{settings.PAYU_CONFIRMATION_URL}" />
      </form>
      <script>document.getElementById('payuForm').submit();</script>
    </body></html>
    """
    return HttpResponse(form_html)


@csrf_exempt
def payu_confirmation(request):
    """
    Webhook de PayU: actualiza estado del pedido.
    """
    data = request.POST.dict()
    merchant_id = data.get("merchant_id")
    reference_sale = data.get("reference_sale")   # Ej: "MOTO-19"
    value = data.get("value")
    currency = data.get("currency")
    state_pol = data.get("state_pol")
    sign_received = data.get("sign")

    # Generar la firma esperada (con HMAC-SHA256 en confirmation)
    expected_sign = generate_confirmation_signature(
        settings.PAYU_API_KEY,
        merchant_id,
        reference_sale,
        value,
        currency,
        state_pol,
        secret_key=settings.PAYU_API_KEY
    )

    if expected_sign == sign_received:
        try:
            # La referencia ahora es "MOTO-{pedido_id}"
            pedido_id = int(reference_sale.split("-")[1])
            pedido = Pedido.objects.filter(id=pedido_id).first()

            # Guardamos o actualizamos la transacción
            Transaccion.objects.update_or_create(
                id_transaccion_payu=data.get("transaction_id"),
                defaults={
                    'pedido': pedido,
                    'estado_pol': state_pol,
                    'mensaje_respuesta': data.get("response_message_pol"),
                    'metodo_pago_nombre': data.get("payment_method_name"),
                    'valor': Decimal(value),
                    'moneda': currency,
                }
            )


            if pedido:
                if state_pol == "4" and pedido.estado == 'Pendiente':  # Pago APROBADO y pedido aún pendiente
                    with transaction.atomic():
                        # 1. Actualizar el estado del pedido
                        pedido.estado = "Procesando"
                        pedido.save()

                        # 2. Descontar el stock de cada producto en el pedido
                        for item_carrito in pedido.carritos.all():
                            producto = item_carrito.producto
                            # Restamos la cantidad comprada del stock del producto
                            producto.stock -= item_carrito.cantidad
                            producto.save()

                elif state_pol in ["5", "6"]:  # expirado o rechazado
                    if pedido.estado == 'Pendiente':
                        pedido.estado = "Cancelado"
                        pedido.save()
        except Exception as e:
            # Es buena práctica registrar el error
            print("Error procesando confirmation:", e)

        return HttpResponse("OK")

    return HttpResponse("Invalid signature", status=400)



@csrf_exempt
def payu_response(request):
    """
    Vista visible al usuario tras pagar en PayU.
    """
    params = request.POST.dict() if request.method == "POST" else request.GET.dict()
    state_pol = params.get("state_pol")
    return render(request, "tienda/payu_response.html", {F"params": params, "state_pol": state_pol})




#index
def index(request):
    productos = Producto.objects.all()
    categorias = Categoria.objects.all()
    return render(request, 'tienda/index/index.html', {'productos': productos , 'categorias': categorias})

# productos por categoria
def productos_por_categoria(request, categoria_id):
    categorias = Categoria.objects.all()
    categoria = get_object_or_404(Categoria, id=categoria_id)
    productos = Producto.objects.filter(categoria=categoria)
    return render(request, 'tienda/index/productos_por_categoria.html', {
        'productos': productos,
        'categoria': categoria,
        'categorias': categorias
    })
    
#detalle producto
def producto_detalle(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    # Obtenemos otros productos de la misma categoría para mostrarlos como sugerencias
    imagenes_adicionales = producto.imagenes_adicionales.all()

    productos_relacionados = Producto.objects.filter(categoria=producto.categoria).exclude(id=producto_id)[:4]
    return render(request, 'tienda/index/producto_detalle.html', {
        'producto': producto,
        'productos_relacionados': productos_relacionados,
        'imagenes_adicionales': imagenes_adicionales,
    })



def detalles_facturacion(request):
    return render(request, 'tienda/detalles_factura.html')

#catalogo
from django.db.models import Q
def catalogo(request):
    query = request.GET.get('q', '')
    productos = Producto.objects.all()
    if query:
        productos = productos.filter(
            Q(nombre__icontains=query) |
            Q(descripcion__icontains=query) |
            Q(categoria__nombre__icontains=query)
        )
    return render(request, 'tienda/index/catalogo.html', {'productos': productos, 'query': query})



#admin
def productos(request):
    if request.method == 'POST':
        print("DEBUG request.FILES keys:", list(request.FILES.keys()))
        form = ProductoForm(request.POST, request.FILES)
        if not form.is_valid():
            print("DEBUG form errors:", form.errors)  # ver qué campo falla
        if form.is_valid():
            producto = form.save()
            # revisar varios nombres posibles para los ficheros según tu plantilla
            files = request.FILES.getlist('imagenes_adicionales') or \
                    request.FILES.getlist('imagenes') or \
                    request.FILES.getlist('imagen') or []
            for f in files:
                ProductoImagen.objects.create(producto=producto, imagen=f)
            messages.success(request, "Producto agregado correctamente.")
            return redirect('productos')
        else:
            messages.error(request, "Corrige los errores del formulario.")
    else:
        form = ProductoForm()
    productos_qs = Producto.objects.all()
    categorias_qs = Categoria.objects.all()  # Obtenemos todas las categorías
    return render(request, 'tienda/admin/productos/productos.html', {
        'productos': productos_qs,
        'formulario': form,
        'categorias': categorias_qs,  # Las pasamos al contexto
    })

#eliminar producto admin
def eliminar_producto(request, id):
    producto = get_object_or_404(Producto, id=id)
    producto.delete()
    return redirect('productos')

# editar producto 
def editar_producto(request, producto_id=None, id=None):
    """Editar un producto existente y sus imágenes."""
    # Obtener el ID del producto (sea por producto_id o id)
    pk = producto_id or id
    producto = get_object_or_404(Producto, id=pk)

    if request.method == 'POST':
        # Actualizar datos básicos del producto
        producto.nombre = request.POST.get('nombre', producto.nombre)
        producto.modelo = request.POST.get('modelo', producto.modelo)
        producto.descripcion = request.POST.get('descripcion', producto.descripcion)
        producto.precio = request.POST.get('precio', producto.precio)
        producto.stock = request.POST.get('stock', producto.stock)

        # Actualizar categoría si se proporciona
        categoria_id = request.POST.get('categoria')
        if categoria_id:
            categoria = get_object_or_404(Categoria, id=categoria_id)
            producto.categoria = categoria

        
        # Si viene una nueva imagen principal
        if 'imagen' in request.FILES:
            # Opcional: eliminar imagen anterior
            if producto.imagen:
                producto.imagen.delete()
            producto.imagen = request.FILES['imagen']

        try:
            # Guardar cambios del producto
            producto.save()
            
            # Procesar imágenes adicionales si hay
            imagenes = request.FILES.getlist('imagenes_adicionales')
            for imagen in imagenes:
                ProductoImagen.objects.create(
                    producto=producto,
                    imagen=imagen
                )
            
            messages.success(request, "Producto actualizado correctamente.")
        except Exception as e:
            messages.error(request, f"Error al actualizar el producto: {str(e)}")
            
    return redirect('productos')


#eliminar imagenes producto
@login_required
def eliminar_imagenes_producto(request, id):
    if request.method == 'POST':
        producto = get_object_or_404(Producto, id=id)
        # Eliminar todas las imágenes adicionales asociadas
        for img_adicional in producto.imagenes_adicionales.all():
            img_adicional.imagen.delete() # Borra el archivo
            img_adicional.delete() # Borra el registro de la BD
        messages.success(request, "Se eliminaron todas las imágenes adicionales del producto.")
    return redirect('productos')


# CATEGORIAS
def categorias(request):
    if request.method == 'POST':
        formulario = categoriaForm(request.POST)
        if formulario.is_valid():
            formulario.save()
            messages.success(request, "Categoría agregada exitosamente.")
            return redirect('categorias')
    else:
        formulario = categoriaForm()
    categorias = Categoria.objects.all()
    return render(request, 'tienda/admin/categorias/categorias.html', {
        'categorias': categorias,
        'formulario': formulario
    })

#eliminar categoria 
def eliminar_categoria(request, id):
    categoria = get_object_or_404(Categoria, id=id)
    categoria.delete()
    return redirect('categorias')

# editar categoria
def editar_categoria(request, id):
    categoria = get_object_or_404(Categoria, id=id)
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        if nombre:
            categoria.nombre = nombre
            categoria.save()
            messages.success(request, "Categoría actualizada correctamente.")
        return redirect('categorias')


#USUARIOS
def usuarios(request):
    # Si se envía el formulario del modal para crear un admin
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        if not email or not password:
            messages.error(request, "El email y la contraseña son obligatorios.")
            return redirect('usuarios')

        if User.objects.filter(email=email).exists():
            messages.error(request, f"El correo electrónico '{email}' ya está en uso.")
            return redirect('usuarios')

        # Creamos el usuario como staff para que pueda acceder al admin
        admin_user = User.objects.create_user(username=email, email=email, password=password, is_staff=True)
        
        # La señal se encargará de crear el perfil 'Usuario' y asignarle el rol 'Cliente'.
        # Opcional: Si quieres un rol 'Admin', lo asignamos aquí.
        admin_rol, _ = Rol.objects.get_or_create(nombre='Administrador')
        admin_user.perfil.rol = admin_rol
        admin_user.perfil.save()

        messages.success(request, f"Administrador '{email}' creado exitosamente.")
        return redirect('usuarios')

    # Para la petición GET, mostramos la lista de usuarios
    lista_usuarios = Usuario.objects.select_related('user', 'rol').order_by('-user__date_joined')
    return render(request, 'tienda/admin/usuarios/usuario_admin.html', {'usuarios': lista_usuarios})

#eliminar usuario
def eliminar_usuario(request, id):
    usuario = get_object_or_404(Usuario, id=id)
    usuario.delete()
    return redirect('usuarios')


#index admin
# ...existing code...
from django.db.models import Sum, Count
from datetime import datetime, timedelta
import json
# ...existing code...

def index_admin(request):
    """
    Dashboard admin: prepara KPIs, series de ventas (últimos 30 días),
    top productos por unidades vendidas, estado de pedidos y pedidos recientes.
    """
    # 1. Obtener y validar el rango de fechas desde el request
    today = datetime.now().date()
    end_date_str = request.GET.get('end_date', today.strftime('%Y-%m-%d'))
    start_date_str = request.GET.get('start_date', (today - timedelta(days=29)).strftime('%Y-%m-%d'))

    try:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        end_date = today
        start_date = today - timedelta(days=29)

    if start_date > end_date:
        start_date, end_date = end_date, start_date # Swap

    # KPIs básicos
    total_productos = Producto.objects.count()
    total_usuarios = Usuario.objects.count()
    total_categorias = Categoria.objects.count()
    total_pedidos = Pedido.objects.filter(fecha__date__range=[start_date, end_date]).count()
    
    # Consideramos solo pedidos pagados para los ingresos
    pedidos_pagados = Pedido.objects.filter(estado__in=['Procesando', 'Entregado'], fecha__date__range=[start_date, end_date])

    # Ventas en el rango de fechas (por día)
    sales_labels = []
    sales_data = []
    delta = end_date - start_date
    for i in range(delta.days + 1):
        day = start_date + timedelta(days=i)
        sales_labels.append(day.strftime("%d %b"))
        day_total = (
            pedidos_pagados.filter(fecha__date=day)
            .aggregate(total=Sum('total'))['total'] or 0
        )
        sales_data.append(float(day_total))

    # Top productos por unidades vendidas en el rango de fechas
    top_products_qs = (
        CarritoProductoPedido.objects
        .filter(pedido__estado__in=['Procesando', 'Entregado'],
                pedido__fecha__date__range=[start_date, end_date])
        .values('producto__id', 'producto__nombre')
        .annotate(units_sold=Sum('cantidad'))
        .order_by('-units_sold')[:6]
    )
    top_products_labels = [p['producto__nombre'] for p in top_products_qs]
    top_products_data = [int(p['units_sold'] or 0) for p in top_products_qs]

    # Estado de pedidos (conteo por estado) en el rango de fechas
    orders_status_qs = (
        Pedido.objects.filter(fecha__date__range=[start_date, end_date])
        .values('estado')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    orders_status_labels = [o['estado'] for o in orders_status_qs]
    orders_status_data = [int(o['count']) for o in orders_status_qs]

    # Pedidos recientes (últimos 8)
    recent_orders_qs = (
        Pedido.objects.select_related('usuario__user')
        .order_by('-fecha')[:8]
    )
    recent_orders = []
    for p in recent_orders_qs:
        recent_orders.append({
            'id': p.id,
            'user_name': getattr(p.usuario.user, 'get_full_name', lambda: "")() or p.usuario.user.username,
            'user_email': p.usuario.user.email, # Mantener email por si el nombre no está
            'total': float(p.total or 0),
            'status': p.estado,
            'created_at': p.fecha.strftime("%Y-%m-%d %H:%M") if getattr(p, 'fecha', None) else ''
        })

    # Productos con bajo stock
    low_stock_products = Producto.objects.filter(stock__lte=5).order_by('stock')[:8]

    # Productos que nunca se han vendido
    sold_product_ids = (
        CarritoProductoPedido.objects
        .filter(pedido__estado__in=['Procesando', 'Entregado'])
        .values_list('producto_id', flat=True).distinct()
    )
    unsold_products = Producto.objects.exclude(id__in=sold_product_ids).order_by('nombre')[:5]

    context = {
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'total_productos': total_productos,
        'total_usuarios': total_usuarios,
        'total_categorias': total_categorias,
        'total_pedidos': total_pedidos,
        'sales_labels': json.dumps(sales_labels),
        'sales_data': json.dumps(sales_data),
        'top_products_labels': json.dumps(top_products_labels),
        'top_products_data': json.dumps(top_products_data),
        'orders_status_labels': json.dumps(orders_status_labels),
        'orders_status_data': json.dumps(orders_status_data),
        'recent_orders': recent_orders,
        'low_stock_products': low_stock_products,
        'unsold_products': unsold_products,
        'currency': getattr(settings, 'PAYU_CURRENCY', 'COP'),
    }

    return render(request, 'tienda/admin/index_admin.html', context)


def base_admin(request):
    return render(request, 'tienda/admin/base_admin.html')




#Perfil
@login_required
def perfil(request):
    # Obtener el usuario autenticado
    user = request.user  # Modelo User de Django
    usuario = user.perfil # Accedemos al perfil directamente gracias al related_name

    if request.method == 'POST':
        # Actualizar los campos del modelo User
        user.first_name = request.POST.get('nombre_completo', user.first_name)
        new_email = request.POST.get('correo_electronico')
        if new_email and new_email != user.email:
            if user.__class__.objects.filter(email=new_email).exclude(pk=user.pk).exists():
                messages.error(request, "El correo electrónico ya está en uso.")
            else:
                user.email = new_email
        
        # Actualizar los campos del modelo Usuario
        usuario.telefono = request.POST.get('telefono', usuario.telefono)
        usuario.direccion = request.POST.get('direccion', usuario.direccion)
        usuario.direccion2 = request.POST.get('direccion2', usuario.direccion2)
        usuario.ciudad = request.POST.get('ciudad', usuario.ciudad)
        usuario.departamento = request.POST.get('departamento', usuario.departamento)
        usuario.cedula = request.POST.get('cedula', usuario.cedula)
        
        user.save()
        usuario.save()
        
        messages.success(request, "Perfil actualizado correctamente.")
        return redirect('perfil')

    # Obtener los pedidos del usuario
    # Optimizamos la consulta para incluir los productos de cada pedido
    pedidos = Pedido.objects.filter(usuario=usuario).prefetch_related('carritos__producto').order_by('-fecha')

    return render(request, 'tienda/index/perfil.html', {
        'user': user,  # Usuario autenticado de Django
        'usuario': usuario,  # Modelo personalizado Usuario
        'pedidos': pedidos
    })


# plantilla
def tablas_bootstrap(request):
    return render(request, 'tienda/admin/pedidos/tables-bootstrap-tables.html')

def transactions(request):
    lista_transacciones = Transaccion.objects.select_related('pedido__usuario__user').order_by('-fecha')
    return render(request, 'tienda/admin/pedidos/transactions.html', {'transacciones': lista_transacciones})

def transaction_detail(request, transaction_id):
    transaccion = get_object_or_404(Transaccion.objects.select_related('pedido__usuario__user'), id=transaction_id)
    return render(request, 'tienda/admin/pedidos/transaction_detail.html', {
        'transaccion': transaccion
    })


# Detalles de facturación
@login_required
def detalles_facturacion(request):
    usuario = request.user.perfil   # el perfil extendido

    # Limpiamos los mensajes antiguos para que no se muestren en esta página
    # a menos que se generen por una acción aquí mismo.
    list(messages.get_messages(request))
    

    if request.method == "POST":
        usuario.telefono = request.POST.get("telefono", usuario.telefono)
        usuario.cedula = request.POST.get("cedula", usuario.cedula)
        usuario.direccion = request.POST.get("direccion", usuario.direccion)
        usuario.direccion2 = request.POST.get("direccion2", usuario.direccion2)
        usuario.ciudad = request.POST.get("ciudad", usuario.ciudad)
        usuario.departamento = request.POST.get("departamento", usuario.departamento)
        usuario.save()

        request.user.email = request.POST.get("correo_electronico", request.user.email)
        request.user.first_name = request.POST.get("nombre_completo", request.user.first_name)
        request.user.save()

        messages.success(request, "Detalles de facturación guardados correctamente ✅")
        

    return render(request, "tienda/detalles_factura.html", {
        "usuario": usuario,
        
    })




# pedidos
def pedidos(request):
    # Optimizamos la consulta para incluir datos del usuario y evitar consultas extra en la plantilla
    lista_pedidos = Pedido.objects.select_related('usuario__user').order_by('-fecha')
    return render(request, 'tienda/admin/pedidos/pedidos.html', {
        'pedidos': lista_pedidos
    })

def pedido_detalle(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    carritos = CarritoProductoPedido.objects.filter(pedido=pedido)

    # obtenemos transacciones relacionadas
    transacciones = Transaccion.objects.filter(pedido=pedido).order_by('-fecha')

    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado')
        if nuevo_estado in [estado[0] for estado in Pedido.ESTADOS]:
            pedido.estado = nuevo_estado
            pedido.save()
            messages.success(request, f"El estado del pedido #{pedido.id} ha sido actualizado a '{nuevo_estado}'.")
            return redirect('pedido_detalle', pedido_id=pedido.id)

    return render(request, 'tienda/admin/pedidos/pedido_detalle.html', {
        'pedido': pedido,
        'carritos': carritos,
        'estados_posibles': Pedido.ESTADOS,
        'transacciones': transacciones,   # <-- nuevo
    })

#crear pedido
@login_required
@csrf_exempt
def crear_pedido(request):
    if request.method == "POST":
        data = json.loads(request.body)

        # Usar el perfil asociado al User
        usuario = request.user.perfil  

        # Asignar el primer método de pago disponible (ej. PayU) por defecto.
        # Asegúrate de tener al menos un método de pago en tu base de datos.
        

        pedido = Pedido.objects.create(
            usuario=usuario,
            
            total=sum(float(item["price"]) * int(item["quantity"]) for item in data["carrito"]),
            estado="Pendiente"
        )

        for item in data["carrito"]:
            producto = get_object_or_404(Producto, id=item["id"])
            CarritoProductoPedido.objects.create(
                pedido=pedido,
                producto=producto,
                cantidad=item["quantity"],
                total=float(item["price"]) * int(item["quantity"])
            )

        return JsonResponse({"success": True, "pedido_id": pedido.id})

    return JsonResponse({"success": False})
