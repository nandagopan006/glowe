from django.shortcuts import render,redirect,get_object_or_404
from .forms import CategoryForm
from django.contrib import messages

from .models import Category
from django.db.models import Count
from django.core.paginator import Paginator



def category_management(request):   
    
    q = request.GET.get('q','').strip()
    active_status=request.GET.get('active_status','')
    status=request.GET.get('status','live')
    
    qs= Category.objects.all().annotate(product_count=Count('products'))
    
    if q:
        qs=qs.filter(name__icontains=q)
        
    if active_status =="active":
        qs =qs.filter(is_active=True)
    elif active_status =='inactive':
        qs=qs.filter(is_active=False)
        
    if status == 'archived' :
        qs=qs.filter(is_deleted=True)
    else :
        qs=qs.filter(is_deleted=False)
    
    #sort
    qs=qs.order_by('-created_at')
    
    paginator=Paginator(qs,5)
    page_number=request.GET.get('page')
    categories=paginator.get_page(page_number)
    
    
    total=Category.objects.filter(is_deleted=False).count()
    active=Category.objects.filter(is_active=True, is_deleted=False).count()
    inactive=Category.objects.filter(is_active=False, is_deleted=False).count()
    archived_count = Category.objects.filter(is_deleted=True).count()
    context={
        'query': q,
        'categories':categories,
        'status': status,
        'active_status':active_status,
        'total_categories':total,
        'active_categories':active,
        'inactive_categories':inactive,
        'archived_count':archived_count
    }
    
    return render(request,'category_management.html',context)


def add_category(request):
    
    if request.method =='POST' :
        form = CategoryForm(request.POST)
        
        if form.is_valid():
            form.save()
            messages.success(request,'category is created successfully')
            return redirect('category_management') 
            
        else:
            
            # If form invalid, show errors
            for errors in form.errors.values():
                for e in errors:
                    messages.error(request, e)
    
    return redirect('category_management')

def edit_category(request,id):
    
    category=get_object_or_404(Category,id=id,is_deleted=False)
    
    if request.method == 'POST':
        form = CategoryForm(request.POST,instance=category)
        
        if form.is_valid():
            form.save()
            messages.success(request,'category successfully updated....')
        else :
            for errors in form.errors.values():
                for e in errors:
                    messages.error(request, e)
    
    return redirect('category_management')

def toggle_category(request, id):

    if request.method!='POST':
        return redirect('category_management')
    
    category=get_object_or_404(Category, id=id)
    
    if category.is_deleted:
        messages.error(request,"Cannot modify archived category")
        return redirect('category_management')
    
    category.is_active=not category.is_active
    category.save()
    active_status = 'activated' if category.is_active else 'deactivated'
    messages.success(request,f'{category.name}  has been {active_status}.')
    return redirect('category_management')

def soft_delete_category(request,id):
    if request.method =="POST":
        category=get_object_or_404(Category,id=id,)
        if category.is_deleted:
            messages.error(request, "Category already archived")
            return redirect('category_management')
        
        category.is_deleted=True
        category.save()
        
        messages.success(request,f'{category.name}  has been archived. ')
        return redirect('category_management')
    return redirect('category_management')

def restore_category(request,id):
    if request.method == "POST":
        category=get_object_or_404(Category,id=id,is_deleted=True)
        category.is_deleted = False 
        category.save()
        messages.success(request,f'{category.name}  has been successfully restored')
        return redirect('category_management')

    return redirect("category_management")
        
def permanent_delete_category(request, id):
    if request.method =="POST":
        category =get_object_or_404(Category, id=id)
        
        if not category.is_deleted == True:
            messages.error(request,"Please soft delete the category first then only allow")
            return redirect('category_management')
        
        if category.products.exists():
            messages.error(request, "Cannot delete category with products")
            return redirect('category_management')

        category.delete() # permanent deleete

        messages.success(request,"category permanently deleted")
        return redirect('category_management')       
        

# Create your views here.
