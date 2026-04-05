from django.urls import path,include
from . import views

urlpatterns = [
    path('cart/',views.cart,name='cart'),
    path('cart/update/',views.update_cart,name='update_cart'),
    path('cart/remove/<int:item_id>/',views.remove_from_cart, name='remove_from_cart'),
    path('checkout/',views.checkout,name='checkout'),
]