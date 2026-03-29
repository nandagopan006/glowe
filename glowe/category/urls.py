from django.urls import path,include
from . import views

urlpatterns = [
   
     path('adminpanel/categories/',views.category_management,name='category_management'),
     path('adminpanel/categories/add/',views.add_category,name='add_category'),
     path('adminpanel/categories/edit/<int:id>/',views.edit_category,name='edit_category'),
     path('adminpanel/categories/soft-delete/<int:id>/',views.soft_delete_category,name='soft_delete_category'),
     path('adminpanel/categories/toggle-category/<int:id>/',views.toggle_category,name='toggle_category'),
     path('categories/restore/<int:id>',views.restore_category, name='restore_category'),
     path('adminpanel/categories/per-delete/<int:id>/',views.permanent_delete_category,name='permanent_delete_category'),

]