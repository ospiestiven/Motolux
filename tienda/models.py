from django.db import models
from django.contrib.auth.models import User
from django import forms
from django.core.validators import MinValueValidator

class Rol(models.Model):
    nombre = models.CharField(max_length=255)

    def __str__(self):
        return self.nombre





class Categoria(models.Model):
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre

    # Método para filtrar productos por categoría
    def obtener_productos(self):
        return self.productos.all()


class Producto(models.Model):
    nombre = models.CharField(max_length=200,verbose_name="Nombre")
    modelo = models.CharField(max_length=100, blank=True, null=True, verbose_name="Modelo de Moto")
    descripcion = models.TextField(max_length=200,verbose_name="Descripción")
    precio = models.DecimalField(max_digits=10, decimal_places=0, validators=[MinValueValidator(0)],verbose_name="Precio")
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, related_name='productos',verbose_name="Categoría")
    imagen = models.ImageField(upload_to='productos/', verbose_name="Imagen")
    stock = models.PositiveIntegerField(default=0,verbose_name="Stock")

    def __str__(self):
        fila = f"ID: {self.id}, Nombre: {self.nombre}, Precio: {self.precio}, Stock: {self.stock}"
        return fila
    
    def delete (self, using=None, keep_parents=False):
        self.imagen.storage.delete(self.imagen.name)  # Elimina la imagen del sistema de archivos
        super().delete()


class ProductoImagen(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='imagenes_adicionales')
    imagen = models.ImageField(upload_to='productos/adicionales/', verbose_name="Imagen Adicional")

    def __str__(self):
        return f"Imagen para {self.producto.nombre}"


class Usuario(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="perfil")
    rol = models.ForeignKey("Rol", on_delete=models.CASCADE, related_name='usuarios')

    # 🔹 Campos extra que no trae el modelo User
    telefono = models.CharField(max_length=20, blank=True, null=True)
    cedula = models.CharField(max_length=20, blank=True, null=True)
    direccion = models.CharField(max_length=200, blank=True, null=True)
    direccion2 = models.CharField(max_length=200, blank=True, null=True)
    ciudad = models.CharField(max_length=100, blank=True, null=True)
    departamento = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username


    


class Pedido(models.Model):
    ESTADOS = [
        ('Pendiente', 'Pendiente'),
        ('Procesando', 'Procesando'),
        ('Entregado', 'Entregado'),
        ('Cancelado', 'Cancelado'),
    ]

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='pedidos')
    
    fecha = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=0, validators=[MinValueValidator(0)])
    estado = models.CharField(max_length=20, choices=ESTADOS, default='Pendiente')

    def __str__(self):
        return f"Pedido {self.id} - Usuario: {self.usuario.user.username}"



class CarritoProductoPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='carritos')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='carritos')
    cantidad = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    total = models.DecimalField(max_digits=10, decimal_places=0, validators=[MinValueValidator(0)])

    def __str__(self):
        return f"Carrito {self.id} - Pedido: {self.pedido.id}"


class Transaccion(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.SET_NULL, null=True, related_name='transacciones')
    id_transaccion_payu = models.CharField(max_length=255, unique=True, help_text="Transaction ID de PayU")
    estado_pol = models.CharField(max_length=50, help_text="Estado de la transacción en PayU")
    mensaje_respuesta = models.CharField(max_length=255, help_text="Mensaje de respuesta de PayU")
    metodo_pago_nombre = models.CharField(max_length=100, help_text="Nombre del método de pago usado")
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    moneda = models.CharField(max_length=10)
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Transacción {self.id_transaccion_payu} para Pedido {self.pedido.id}"