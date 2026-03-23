from django.urls import path,include
from . import views


urlpatterns = [
   
     path('admin-signin/',views.admin_signin,name='admin_signin'),
     path('admin-dashboard/',views.admin_dashboard,name='admin_dashboard'),
     path('admin-signout/',views.admin_signout,name='admin_signout'),
     path('admin-forget-password/',views.admin_forget_password,name='admin_forget_password'),
     path('admin-otp-verification/',views.admin_otp_verification,name='admin_otp_verification'),
     path('admin-reset-password/',views.admin_reset_password,name='admin_reset_password'),
     path('admin-resent-otp/',views.admin_resend_otp,name='admin_resend_otp'),
      path('user-management/',views.user_management,name='user_management'),
      path("admin-toggle-block/<int:id>/", views.admin_toggle_block , name='admin_toggle_block'),
      path('user-detail/<int:id>/',views.user_detail,name='user_detail'),
     
]