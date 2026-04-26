from django.urls import path
from . import views

urlpatterns = [


    path('adminpanel/products/',views.product_management,name='product_management'),
     path('adminpanel/product-detail/<int:id>/',views.product_detail,name='product_detail'),
    path('adminpanel/products/add/', views.add_product,name='add_product'),
    path('adminpanel/products/edit/<int:id>/',views.edit_product,name='edit_product'),

    path('adminpanel/products/delete/<int:id>/',views.soft_delete_product,name='soft_delete_product'),
    path('adminpanel/products/restore/<int:id>/',views.restore_product, name='restore_product'),
    path('adminpanel/products/permanent-delete/<int:id>/',views.permanent_delete_product,name='permanent_delete_product'),

    path('adminpanel/products/toggle-status/<int:id>/',views.toggle_product_status,name='toggle_product_status'),

    path('adminpanel/products/image/delete/<int:id>/',views.delete_product_image,name='delete_product_image'),
    path('adminpanel/products/image/set-primary/<int:id>/',views.set_primary_image,name='set_primary_image'),

       path('adminpanel/products/<int:product_id>/variants/', views.variant_management, name='variant_management'),

   
    path('adminpanel/products/variants/add/<int:product_id>/', views.add_variant, name='add_variant'),
    path('adminpanel/products/variants/edit/<int:id>/', views.edit_variant, name='edit_variant'),
    path('adminpanel/products/variants/delete/<int:id>/', views.delete_variant, name='delete_variant'),
    path('adminpanel/products/variants/toggle-status/<int:id>/', views.toggle_variant_status, name='toggle_variant_status'),
    path('adminpanel/products/variants/set-default/<int:id>/', views.set_default_variant, name='set_default_variant'),
    
    
    path('products/',views.product_listing, name='product_listing'),
    path('product/detail/<slug:slug>/',views.product_detail_view, name='product_detail_view'),
    path('add-to-cart/',views.add_to_cart,name='add_to_cart'),
    path('check-cart-status/', views.check_cart_status, name='check_cart_status'),
    
    
    
    
    
    
]