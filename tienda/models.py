from django.db import models
from django.contrib.auth.models import User
from django import forms
from django.core.validators import MinValueValidator

class Rol(models.Model):
    nombre = models.CharField(max_length=255)

    def __str__(self):
        return self.nombre


class MetodoPago(models.Model):
    tipo = models.CharField(max_length=100)

    def __str__(self):
        return self.tipo


class Categoria(models.Model):
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre

    # Método para filtrar productos por categoría
    def obtener_productos(self):
        return self.productos.all()


class Producto(models.Model):
    nombre = models.CharField(max_length=200,verbose_name="Nombre")
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
    metodo_pago = models.ForeignKey(MetodoPago, on_delete=models.CASCADE, related_name='pedidos')
    fecha = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    estado = models.CharField(max_length=20, choices=ESTADOS, default='Pendiente')

    def __str__(self):
        return f"Pedido {self.id} - Usuario: {self.usuario.user.username}"



class CarritoProductoPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='carritos')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='carritos')
    cantidad = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    total = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])

    def __str__(self):
        return f"Carrito {self.id} - Pedido: {self.pedido.id}"