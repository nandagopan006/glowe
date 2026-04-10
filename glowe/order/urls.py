from django.urls import path
from order import views

urlpatterns = [
path('place-order/',views.place_order,name='place_order'),
path('order-success/<int:order_id>/',views.order_success,name='order_success'),

path('orders/',views.order_listing,name='order_listing'),
path('order-detail/<int:order_id>/',views.order_detail,name='order_detail'),
path('order-detail/<int:order_id>/cancel/',views.cancel_order,name='cancel_order'),
path('order-detail/item/<int:item_id>/cancel/',views.cancel_order_item,name='cancel_order_item'),
path('order-cancelled/<int:order_id>/',views.order_cancelled_success,name='order_cancelled_success'),
path('order/<int:order_id>/invoice/',views.download_invoice,name='download_invoice'),



path('admin-panel/orders/',views.admin_order_list,name='admin_order_list'),
path('admin-panel/orders/<int:order_id>/',views.admin_order_detail,name='admin_order_detail'),
path('admin-panel/orders/<int:order_id>/update-status/',views.update_order_status,name='update_order_status'),
]