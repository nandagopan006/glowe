from django.urls import path
from . import views

urlpatterns = [
path('place-order/',views.place_order,name='place_order'),
path('order-success/<int:order_id>/',views.order_success,name='order_success'),

path('orders/', views.order_listing, name='order_listing'),
path('order-detail/<int:order_id>/',views.order_detial,name='order_detial'),
path('order-detail/<int:order_id>/cancel/',views.cancel_order,name='cancel_order'),
path('order-detail/item/<int:item_id>/cancel/', views.cancel_order_item, name='cancel_order_item'),

]