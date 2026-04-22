from django.urls import path,include
from . import views

urlpatterns = [
    path("offers/", views.offer_list, name="offer_list"),
    path("offers/add/", views.add_offer, name="add_offer"),
    path("offers/edit/<int:id>/", views.edit_offer, name="edit_offer"),
    path("offers/delete/<int:id>/", views.delete_offer, name="delete_offer"),
    path("offers/toggle/<int:id>/", views.toggle_offer, name="toggle_offer"),
]