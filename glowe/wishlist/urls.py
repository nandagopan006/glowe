from django.urls import path
from . import views

urlpatterns = [
    path("wishlist/", views.wishlist_page, name="wishlist"),
    path("wishlist/add/<int:variant_id>/", views.add_to_wishlist, name="add_to_wishlist"),
]