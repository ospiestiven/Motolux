

from django.contrib import admin
from .models import Categoria, Producto, Rol, MetodoPago, Usuario, Pedido, CarritoProductoPedido

# Personalización del modelo Categoria
@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')  # Mostrar columnas en la lista
    search_fields = ('nombre',)  # Agregar barra de búsqueda


# Personalización del modelo Producto
@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'categoria', 'precio', 'stock')  # Mostrar columnas
    list_filter = ('categoria',)  # Agregar filtros por categoría
    search_fields = ('nombre', 'descripcion')  # Agregar barra de búsqueda


# Personalización del modelo Rol
@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')
    search_fields = ('nombre',)


# Personalización del modelo MetodoPago
@admin.register(MetodoPago)
class MetodoPagoAdmin(admin.ModelAdmin):
    list_display = ('id', 'tipo')
    search_fields = ('tipo',)


# Personalización del modelo Usuario
@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ("get_email", "rol", "telefono", "ciudad")

    def get_email(self, obj):
        return obj.user.email
    get_email.admin_order_field = "user__email"
    get_email.short_description = "Correo"
    



# Personalización del modelo Pedido
@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'metodo_pago', 'fecha', 'total')
    list_filter = ('metodo_pago', 'fecha')  # Agregar filtros por método de pago y fecha
    search_fields = ('usuario__nombre_completo',)  # Búsqueda por nombre del usuario


# Personalización del modelo CarritoProductoPedido
@admin.register(CarritoProductoPedido)
class CarritoProductoPedidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'pedido', 'producto', 'cantidad', 'total')
    list_filter = ('pedido', 'producto')  # Agregar filtros por pedido y producto
    search_fields = ('producto__nombre',)  # Búsqueda por nombre del producto


# Personalización general del sitio de administración
admin.site.site_header = "Administración de Tienda"
admin.site.site_title = "Motolux"
admin.site.index_title = "Bienvenido a Motolux"
