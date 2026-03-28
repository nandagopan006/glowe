from django.urls import path
from . import views

urlpatterns = [


    path('adminpanel/products/',views.product_management,name='product_management'),
    path('adminpanel/products/add/', views.add_product,name='add_product'),
    path('adminpanel/products/edit/<int:id>/',views.edit_product,name='edit_product'),

    path('adminpanel/products/delete/<int:id>/',views.soft_delete_product,name='soft_delete_product'),
    path('adminpanel/products/restore/<int:id>/',views.restore_product, name='restore_product'),
    path('adminpanel/products/permanent-delete/<int:id>/',views.permanent_delete_product,name='permanent_delete_product'),

    path('adminpanel/products/toggle-status/<int:id>/',views.toggle_product_status,name='toggle_product_status'),

    path('adminpanel/products/image/delete/<int:id>/',views.delete_product_image,name='delete_product_image'),
    path('adminpanel/products/image/set-primary/<int:id>/',views.set_primary_image,name='set_primary_image'),

    path('adminpanel/products/<int:product_id>/variants/',views.variant_management,name='variant_management'),

    path('adminpanel/variants/add/<int:product_id>/',views.add_variant,name='add_variant'),
    path('adminpanel/variants/edit/<int:id>/',views.edit_variant,name='edit_variant'),
    path('adminpanel/variants/delete/<int:id>/',views.delete_variant,name='delete_variant'),
]