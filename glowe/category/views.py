from django.shortcuts import render,redirect,get_object_or_404
from .forms import CategoryForm
from django.contrib import messages

from .models import Category
from django.db.models import Count
from django.core.paginator import Paginator



def category_management(request):   
    
    q = request.GET.get('q','').strip()
    
    qs= Category.objects.filter(is_deleted=False) #.annotate(poduct_count=Count('products'))
    
    if q:
        qs=qs.filter(name__icontains=q)
        
    qs=qs.order_by('-created_at')
    
    paginator=Paginator(qs,6)
    page_number=request.GET.get('page')
    categories=paginator.get_page(page_number)
    
    
    total=Category.objects.filter(is_deleted=False).count()
    active=Category.objects.filter(is_active=True, is_deleted=False).count()
    inactive=Category.objects.filter(is_active=False, is_deleted=False).count()
    context={
        'categories':categories,
        'total_categories':total,
        'active_categories':active,
        'inactive_categories':inactive,
    }
    
    return render(request,'category_management.html',context)


def add_category(request):
    
    if request.method == 'POST' :
        form = CategoryForm(request.POST)
        
        if form.is_valid():
            form.save()
            messages.success(request,'category is created successfully')
            return redirect('category_management') 
            
        else:
            
            # If form invalid, show errors
            for error in form.errors.values():
                messages.error(request, error)
    
    return redirect('category_management')

def edit_category(request,id):
    
    category=get_object_or_404(Category,id=id,is_deleted=False)
    
    if request.method == 'POST':
        form = CategoryForm(request.POST,instance=category)
        
        if form.is_valid():
            form.save()
            messages.success(request,'category successfully updated....')
        else :
            for error in form.errors.values():
                messages.error(request, error[0])
    
    return redirect('category_management')

def toggle_category(request, id):

    if request.method=='POST':
        category=get_object_or_404(Category, id=id, is_deleted=False)
        category.is_active=not category.is_active
        category.save()
        status='activated' if category.is_active else 'deactivated'
        messages.success(request,f'{category.name}   has been {status}.')
    return redirect('category_management')

def delete_category(request,id):
    if request.method =="POST":
        category=get_object_or_404(Category,id=id,is_deleted=False)
        category.is_deleted=True
        category.save()
        
        messages.success(request,f'{category.name}  has been deleted.')
    return redirect('category_management')

# Create your views here.
