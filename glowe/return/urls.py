from django.urls import path
from . import views

urlpatterns = [
    path("return/request/<int:item_id>/", views.request_return, name="request_return"),
]
