from django import forms
from .models import Producto, Usuario, Categoria, Pedido

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = '__all__'
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'precio': forms.NumberInput(attrs={'class': 'form-control'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'imagen': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'categoria': forms.Select(attrs={'class': 'form-control'}),
        }
        
class categoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = '__all__'

from django import forms
from django.contrib.auth.models import User
from .models import Usuario

class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "password")

class UsuarioForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ("rol", "telefono", "cedula", "direccion", "direccion2", "ciudad", "departamento")


