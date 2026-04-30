from django.urls import path
from . import views

urlpatterns = [
     path('review/add/<int:product_id>/<int:order_id>/', views.create_review, name='add_review'),
    
    
    path('admin-panel/reviews/', views.admin_review_list, name='admin_review_list'),
    path('admin-panel/review/<int:review_id>/', views.admin_review_detail, name='admin_review_detail'),
    path('admin-panel/review/<int:review_id>/approve/', views.approve_review, name='approve_review'),
    path('admin-panel/review/<int:review_id>/reject/', views.reject_review, name='reject_review'),
    path('admin-panel/review/delete/<int:review_id>/', views.delete_review, name='delete_review'),
    path('admin-panel/review/<int:review_id>/archive/', views.archive_review, name='archive_review'),
    path('admin-panel/review/<int:review_id>/restore/', views.restore_review, name='restore_review'),
    path('admin-panel/review/<int:review_id>/permanent-delete/', views.permanent_delete_review, name='permanent_delete_review'),
]
