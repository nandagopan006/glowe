from django.urls import path
from . import views

urlpatterns = [
    path("wishlist/",views.wishlist_page,name="wishlist"),
    path('wishlist/toggle/<int:variant_id>/',views.toggle_wishlist,name='toggle_wishlist'),
    path('wishlist/remove/<int:variant_id>/',views.remove_from_wishlist,name='remove_from_wishlist'),
    path('wishlist/clear/',views.clear_wishlist, name='clear_wishlist'),
    
]