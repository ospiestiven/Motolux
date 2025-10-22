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
import time 
from .models import Producto, Rol, Categoria, Usuario, Pedido, CarritoProductoPedido, Transaccion
from .forms import ProductoForm, categoriaForm, UsuarioForm
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
        secret_key=getattr(settings, "PAYU_SECRET_KEY", None)
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
    return render(request, "tienda/payu_response.html", {"params": params, "state_pol": state_pol})




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
    productos_relacionados = Producto.objects.filter(categoria=producto.categoria).exclude(id=producto_id)[:4]
    return render(request, 'tienda/index/producto_detalle.html', {
        'producto': producto,
        'productos_relacionados': productos_relacionados
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
        formulario = ProductoForm(request.POST, request.FILES)
        if formulario.is_valid():
            formulario.save()
            messages.success(request, "Producto agregado exitosamente.")
            return redirect('productos')
    else:
        formulario = ProductoForm()
    productos = Producto.objects.all()
    return render(request, 'tienda/admin/productos/productos.html', {
        'productos': productos,
        'formulario': formulario
    })

#eliminar producto admin
def eliminar_producto(request, id):
    producto = get_object_or_404(Producto, id=id)
    producto.delete()
    return redirect('productos')
# editar producto 
def editar_producto(request, id):
    producto = get_object_or_404(Producto, id=id)
    if request.method == 'POST':
        producto.nombre = request.POST.get('nombre')
        producto.precio = request.POST.get('precio')
        producto.stock = request.POST.get('stock')
        if request.FILES.get('imagen'):
            producto.imagen = request.FILES['imagen']
        producto.save()
        messages.success(request, "Producto editado exitosamente.")
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


def index_admin(request):
    total_productos = Producto.objects.count()
    total_usuarios = Usuario.objects.count()
    total_categorias = Categoria.objects.count()
    total_pedidos = Pedido.objects.count()
    return render(request, 'tienda/admin/index_admin.html', {
        'total_productos': total_productos,
        'total_usuarios': total_usuarios,
        'total_categorias': total_categorias,
        'total_pedidos': total_pedidos,
    })
    return render(request, 'tienda/admin/index_admin.html')


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
