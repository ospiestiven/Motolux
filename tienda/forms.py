from django import forms
from .models import Producto, Categoria, Usuario, ProductoImagen
from django.core.exceptions import ValidationError
import os

# Widget que permite 'multiple' en esta versión de Django
class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

def validate_image_file(file):
    """
    Valida que el archivo sea una imagen de un tipo permitido (jpg, jpeg, png, webp).
    """
    # 1. Validar por tipo de contenido (más seguro)
    allowed_content_types = ['image/jpeg', 'image/png', 'image/webp']
    if file.content_type not in allowed_content_types:
        raise ValidationError("Tipo de archivo no válido. Solo se permiten imágenes JPG, PNG o WEBP.")

    # 2. Validar por extensión (doble chequeo)
    ext = os.path.splitext(file.name)[1].lower()
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.webp']
    if ext not in allowed_extensions:
        raise ValidationError("Extensión de archivo no válida. Solo se permiten .jpg, .jpeg, .png o .webp.")

class ProductoForm(forms.ModelForm):
    imagenes = forms.FileField(
        widget=MultipleFileInput(attrs={'multiple': True, 'class': 'form-control'}),
        required=False,
        label="Imágenes adicionales",
        help_text="Puedes seleccionar múltiples imágenes para el producto a la vez"
    )
    class Meta:
        model = Producto
        # Aquí defines el orden exacto de los campos del modelo
        fields = ['nombre', 'modelo', 'categoria', 'precio', 'stock', 'descripcion', 'imagen']
        labels = {
            'nombre': 'Nombre del producto',
            'modelo': 'Modelo de la moto',
            'descripcion': 'Descripción detallada',
            'precio': 'Precio (sin puntos ni comas)',
            'categoria': 'Categoría del producto',
            'stock': 'Cantidad disponible',
            'imagen': 'Imagen principal del producto'
        }
        
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'modelo': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'precio': forms.NumberInput(attrs={'class': 'form-control'}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'imagen': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control'}),
        }
    
    def clean_imagen(self):
        imagen = self.cleaned_data.get('imagen', False)
        if imagen:
            validate_image_file(imagen)
        return imagen

    def clean_imagenes(self):
        imagenes = self.files.getlist('imagenes')
        if imagenes:
            for img in imagenes:
                validate_image_file(img)
        # Devolvemos los datos originales del campo para que Django continúe
        return self.cleaned_data.get('imagenes')


class ProductoImagenForm(forms.ModelForm):
    # aceptar múltiples archivos para agregar imágenes desde el editar
    imagen = forms.FileField(
        widget=MultipleFileInput(attrs={'multiple': True, 'class': 'form-control'}),
        label="Añadir nuevas imágenes",
        required=False 
    )
    class Meta:
        model = ProductoImagen
        fields = ['imagen']
    
    def clean_imagen(self):
        imagenes = self.files.getlist('imagen')
        if imagenes:
            for img in imagenes:
                validate_image_file(img)
        return self.cleaned_data.get('imagen')
        
class categoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
        }

from django.contrib.auth.models import User

class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "password")

class UsuarioForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ("rol", "telefono", "cedula", "direccion", "direccion2", "ciudad", "departamento")
