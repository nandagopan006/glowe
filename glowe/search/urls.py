from django.urls import path
from . import views

urlpatterns = [
    path('search/', views.search_view, name='search'),
    path('search/suggestions/', views.search_suggestions, name='search_suggestions'),
]
