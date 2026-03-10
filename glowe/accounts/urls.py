from django.urls import path,include
from . import views



urlpatterns = [
    path("", views.signup_page , name = 'signup_page'),
    
]
