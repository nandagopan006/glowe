from django.urls import path,include
from . import views



urlpatterns = [
    path("signup/", views.signup_page , name = 'signup'),
    path('signin/', views.signin_page,name='signin'),
    path('forget-password/',views.forget_password,name='forget_password'),
    path('otp-verfication/',views.otp_verfication,name='otp_verfication'),
    path('reset-password/',views.reset_password,name='reset_password'),
    
    
]
