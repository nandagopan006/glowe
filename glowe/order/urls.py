from django.urls import path
from . import views

urlpatterns = [
path('checkout/place-order/',views.place_order,name='place_order'),
path('order-success/<int:order_id>/',views.order_success,name='order_success'),
]