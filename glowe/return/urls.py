from django.urls import path
from . import views

urlpatterns = [
    path("return/request/<int:item_id>/", views.request_return, name="request_return"),
    path('admin-panel/returns/', views.admin_return_list, name='admin_return_list'),
    path('admin-panel/returns/<int:return_id>/', views.admin_return_detail, name='admin_return_detail'),

    path('admin-panel/returns/<int:return_id>/schedule/', views.schedule_pickup, name='schedule_pickup'),
    path('admin-panel/returns/<int:return_id>/approve/', views.approve_return, name='approve_return'),
    path('admin-panel/returns/<int:return_id>/reject/', views.reject_return, name='reject_return'),
    path('admin-panel/returns/<int:return_id>/complete/', views.complete_return, name='complete_return'),
    path('admin-panel/returns/<int:return_id>/picked/', views.mark_picked, name='mark_picked'),
]
