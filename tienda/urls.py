from django.urls import path, include
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    #payU
    path("payu/checkout/<int:pedido_id>/", views.payu_checkout, name="payu_checkout"),
    path("payu/response/", views.payu_response, name="payu_response"),
    path("payu/confirmation/", views.payu_confirmation, name="payu_confirmation"),


    
    
    #index
    path('', views.index, name='index'),
    # productos por categoria
    path('productos/categoria/<int:categoria_id>/', views.productos_por_categoria, name='productos_por_categoria'),
    #detalle producto
    path('producto/<int:producto_id>/', views.producto_detalle, name='producto_detalle'),
    
    #catalogo
    path('catalogo/', views.catalogo, name='catalogo'),
    
    #google login
    path('accounts/', include('allauth.urls')),
    
    
    #Perfil
    path('perfil/', views.perfil, name='perfil'),
    
    #Carrito
    path('detalles-de-facturacion/', views.detalles_facturacion, name='detalles_facturacion'),
    
    


    
    
    # Admin
    path('index-admin/', views.index_admin, name='index_admin'),
    path('base-admin/', views.base_admin, name='base_admin'),
    # Productos admin
    path('productos/', views.productos, name='productos'),
   
    path('eliminar-producto/<int:id>/', views.eliminar_producto, name='eliminar_producto'),
    path('productos/editar-producto/<int:id>/', views.editar_producto, name='editar_producto'),
   
    # Categorias admin
    path('categorias/', views.categorias, name='categorias'),
    # Agregar 
    
    # Eliminar
    path('eliminar-categoria/<int:id>/', views.eliminar_categoria, name='eliminar_categoria'),
    # Editar
    path('editar-categoria/<int:id>/', views.editar_categoria, name='editar_categoria'),
    
    #USUARIOS admin
    path('usuarios/', views.usuarios, name='usuarios'),
    # Agregar usuario
    path('agregar-usuario/', views.agregar_usuario, name='agregar_usuario'),
    # Eliminar usuario
    path('eliminar-usuario/<int:id>/', views.eliminar_usuario, name='eliminar_usuario'),
    
    #pedidos
    
    path('pedidos/', views.pedidos, name='pedidos'),
    
    path('pedidos/<int:pedido_id>/', views.pedido_detalle, name='pedido_detalle'),
    
    path("crear-pedido/", views.crear_pedido, name="crear_pedido"),

    
    #plantilla
    path('tablas-bootstrap-tables/', views.tablas_bootstrap, name='tablas_bootstrap'),
    path('transactions/', views.transactions, name='transactions'),
   
    
    
    
    
    
    
   
    
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)