from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from .models import Producto, Rol, MetodoPago, Categoria, Usuario, Pedido, CarritoProductoPedido
from django.contrib.auth.hashers import make_password
from .forms import ProductoForm, categoriaForm, UsuarioForm
from django.contrib.auth.hashers import check_password
from django.http import JsonResponse
import json
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required




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
    return render(request, 'tienda/index/producto_detalle.html', {'producto': producto})


def crear_cuenta(request):
    return render(request, 'tienda/auth/crear_cuenta.html')

def detalles_facturacion(request):
    return render(request, 'tienda/detalles_factura.html')



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
    usuarios = Usuario.objects.all()
    return render(request, 'tienda/admin/usuarios/usuario_admin.html', {'usuarios': usuarios})

# Agregar usuario admin
def agregar_usuario(request):
    if request.method == 'POST':
        formulario = UsuarioForm(request.POST)
        correo_electronico = request.POST.get('correo_electronico')
        if Usuario.objects.filter(correo_electronico=correo_electronico).exists():
            messages.error(request, "El correo electrónico ya está registrado.")
        elif formulario.is_valid():
            usuario = formulario.save(commit=False)
            usuario.save()
            messages.success(request, "Usuario agregado exitosamente.")
            return redirect('usuarios')
    else:
        formulario = UsuarioForm()
    return render(request, 'tienda/admin/usuarios/agregar_usuarios.html', {'formulario': formulario})

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
    user = request.user
    # Obtener o crear el perfil de usuario relacionado
    usuario, created = Usuario.objects.get_or_create(
        user=user,
        defaults={
            'rol': Rol.objects.get(nombre='Cliente')  # Asigna un rol por defecto
        }
    )

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
    pedidos = Pedido.objects.filter(usuario=usuario).order_by('-fecha')

    return render(request, 'tienda/index/perfil.html', {
        'user': user,  # Usuario autenticado de Django
        'usuario': usuario,  # Modelo personalizado Usuario
        'pedidos': pedidos
    })


# plantilla
def tablas_bootstrap(request):
    return render(request, 'tienda/admin/home/tables-bootstrap-tables.html')

def transactions(request):
    return render(request, 'tienda/admin/home/transactions.html')



# Detalles de facturación
@login_required
def detalles_facturacion(request):
    usuario = request.user.perfil   # el perfil extendido
    metodos_pago = MetodoPago.objects.all()

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
        "metodos_pago": metodos_pago
    })




# pedidos
def pedidos(request):
    pedidos = Pedido.objects.all()
    carritos = CarritoProductoPedido.objects.all()
    return render(request, 'tienda/admin/pedidos/pedidos.html', {
        'pedidos': pedidos,
        'carritos': carritos
    })
def pedido_detalle(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    carritos = CarritoProductoPedido.objects.filter(pedido=pedido)
    return render(request, 'tienda/admin/pedidos/pedido_detalle.html', {
        'pedido': pedido,
        'carritos': carritos
    })

#crear pedido
@login_required
@csrf_exempt
def crear_pedido(request):
    if request.method == "POST":
        data = json.loads(request.body)

        # Usar el perfil asociado al User
        usuario = request.user.perfil  

        metodo_pago_id = data.get("metodo_pago")
        metodo_pago = get_object_or_404(MetodoPago, id=metodo_pago_id)

        pedido = Pedido.objects.create(
            usuario=usuario,
            metodo_pago=metodo_pago,
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
