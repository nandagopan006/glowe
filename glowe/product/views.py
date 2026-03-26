from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import ProductForm,VariantForm
from .models import ProductImage,Product,Variant
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator  
from django.db.models import Q,Sum


def add_product(request):
    form = ProductForm() # empty form for Get request
    
    if request.method == "POST":
        form=ProductForm(request.POST)
        images=request.FILES.getlist('images')
        
        if form.is_valid():
            if len(images) < 3 :
                messages.error(request,"Please upload at least 3 images")
                return render(request, 'admin/add_product.html',{'form': form})
            
            valid_types = ['image/jpeg','image/png','image/webp',"image/jpg"]
            for img in images:
                
                if img.content_type not in valid_types:
                    messages.error(request,"Only JPG,PNG,WEBP allowed")
                    return render(request,'admin/add_product.html', {'form': form})
          
                if img.size > 2* 1024* 1024:
                    messages.error(request, "Each image must be under 2MB")
                    return render(request,'admin/add_product.html', {'form': form})
        
            product=form.save() #for save product
            
            for i,img in enumerate(images):
                ProductImage.objects.create(
                    product=product,
                    image=img,is_primary= (i == 0),
                )
            
            messages.success(request,"Product added successfully")
            return redirect('product_management')
    
    return render(request,'admin/add_product.html',{'form': form})
        
def edit_product(request,id):
    product=get_object_or_404(Product,id=id)
    
    form=ProductForm(instance=product)
    
    if request.method =="POST" :
        form=ProductForm(request.POST,instance=product)
        images=request.FILES.getlist('images')
        
        if form.is_valid():
            
            if not product.images.exists() and not images:
                messages.error(request,"Product must have at least one image")
                return render(request,'admin/edit_product.html',{'form':form,'product':product})
            
            if images :
            
                valid_type=['image/jpg','image/webp','image/png','image/jpeg']
                
                for img in images:
                    
                    if img.content_type not in valid_type:
                        messages.error(request,f"{img.name} is not valid")
                        return render(request,'admin/edit_product.html',{'form':form,'product': product})
                    
                    if img.size > 2* 1024 *1024 :
                        messages.error(request, f"{img.name} must be under 2MB")
                        return render(request, 'admin/edit_product.html', {'form': form, 'product': product})
                
                for img in images:
                    
                    ProductImage.objects.create(product=product,
                        image=img,is_primary=False
                    )
            form.save()
            
            messages.success(request,"Product updated successfully")
            return redirect('product_management')
        
        return render(request,'admin/edit_product.html',{'form':form,'product':product})
    
def delete_product_image(request,id):
    if request.method == "POST":
    
        image=get_object_or_404(ProductImage,id=id)
        product=image.product
        
        if product.images.count() <= 1:
            messages.error(request,"Product must have at least one image")
            return redirect('edit_product',id=product.id)
        
        #Check if deleting primary image
        is_primary =image.is_primary
        
        image.delete()
        
        #if dlt primary set another one to primary
        if is_primary and product.images.exists():
            
            new_primary=product.images.order_by('id').first()
            
            if new_primary :
                new_primary.is_primary = True
                new_primary.save()
            
        messages.success(request, "Image deleted successfully")
        return redirect('edit_product', id=product.id)
    
    messages.error(request, "Invalid request")
    return redirect('product_management')

def set_primary_image(request,id):
    if request.method == "POST":
        
        image=get_object_or_404(ProductImage,id=id)
        product=image.product
        
        if image.is_primary:
            messages.info(request,"Already primary image")
            return redirect('edit_product',id=product.id)
        
        product.images.update(is_primary=False)
        
        image.is_primary=True
        image.save()
        
        messages.info(request, "Already primary image")
        return redirect('edit_product', id=product.id)
    
    messages.error(request, "Invalid request")
    return redirect('product_management')

def soft_delete_product(request,id):
    if request.method == "POST": 
    
        product=get_object_or_404(Product,id=id,is_deleted=False)
        product.is_deleted=True # soft delete 
        product.save()
        
        messages.success(request,"Product deleted successfully")
        return redirect('product_management')
    
    messages.error(request,"Invalid request")
    return redirect('product_management')

def restore_product(request,id):
    if request.method == "POST":
        
        product=get_object_or_404(Product,id=id,is_deleted=True)
        product.is_deleted=False
        product.save()
        
        messages.success(request,"Product restored")
        return redirect('product_management')
    
    messages.error(request, "Invalid request")
    return redirect('product_management')

def permanent_delete_product(request, id):
    if request.method =="POST":
        product =get_object_or_404(Product, id=id)
        
        if not product.is_deleted == True:
            messages.error(request,"Please soft delete the product first then only allow")
            return redirect('product_management')

        product.delete() # permanent deleete

        messages.success(request,"Product permanently deleted")
        return redirect('product_management')
    
    return redirect('product_management')

    
def product_management(request): 
    
    return render(request,'product_management.html')

    
def add_variant(request,product_id):
    product = get_object_or_404(Product,id=product_id,is_deleted=False)
    
    if request.method =="POST":
        form=VariantForm(request.POST)
        
        if form.is_valid():
            variant=form.save(commit=False)
            variant.product = product
            
            #if stock zero is inactive ok the vrint
            if variant.stock == 0:
                variant.is_active= False
            else :
                variant.is_active=True
            
            #if select as default true  and change pervies default false 
            if variant.is_default:
                product.variants.filter(is_default=True).update(is_default=False)
                
            #If no default exists make this automtly default
            if not product.variants.filter(is_default=True).exists():
                variant.is_default =True 
                 
            variant.save()

            messages.success(request, "Variant added successfully")
            return redirect('variant_management',product_id=product.id)
        else :
            # If invalid  show errors
            variants=product.variants.all().order_by('id')
            return render(request,'admin/variant_management.html',{
                                    'product':product,
                                    'variants':variants,'form':form})
            
        
    return redirect('variant_management',product_id=product.id)

def edit_variant(request,id):
    variant=get_object_or_404(Variant,id=id)
    product=variant.product
    
    if request.method == "POST":
        form =VariantForm(request.POST,instance=variant)
        
        if form.is_valid():
            updated_variant = form.save(commit=False)
            
            if variant.stock == 0:
                variant.is_active= False
            else :
                variant.is_active=True
            
           #  if user select default remove other defaults
            if updated_variant.is_default :
                product.variants.exclude(id=variant.id).filter(is_default=True).update(is_default=False)
                          
             #if no default exists so that make this default
            if not product.variants.exclude(id=variant.id).filter(is_default=True).exists():
                updated_variant.is_default = True

            updated_variant.save()
            
            messages.success(request, "Variant updated successfully")
            return redirect('variant_management', product_id=product.id)

        variants =product.variants.all().order_by('id')
        return render(request,'admin/variant_management.html',{
            'product':product,'variants':variants,
            'form':form,'edit_variant':variant})
    
    return redirect('variant_management',product_id=product.id)

def delete_variant(request,id):
    if request.method == "POST":
        variant=get_object_or_404(Variant,id=id)
        product=variant.product

        #  Prevent dlt last variant
        if product.variants.count() <= 1:
            messages.error(request,"At least one variant is required")
            return redirect('variant_management',product_id=product.id)

         # Check if this default
        if variant.is_default:
            variant.delete()
            # Make another variant deflt
            new_variant=product.variants.first()
            new_variant.is_default=True
            new_variant.save()

        else:
            #Normal delete
            variant.delete()

        messages.success(request,"Variant deleted successfully")
        return redirect('variant_management',product_id=product.id)

    return redirect('product_management')

def variant_management(request,product_id):
    product=get_object_or_404(Product,id=product_id,is_deleted=False)
    status=request.GET.get('status','')
    #searchh
    q =request.GET.get('q','').strip()
    variants=product.variants.all()
    
    if q :
        variants =variants.filter(
            Q(size__icontains=q) | Q(sku__icontains=q)
        )
    if status =="active":
        variants =variants.filter(is_active=True)
    elif status =='inactive':
        variants=variants.filter(is_active=False) 
    
    variants=variants.order_by('id')
    paginator =Paginator(variants,5)
    page_number=request.GET.get('page')
    variants=paginator.get_page(page_number)       
    
    #Product summary
    all_variants=product.variants.all()

    default_variant=product.variants.filter(is_deleted=False).first()
    total_stock=product.variants.aggregate(total=Sum('stock'))['total'] or 0
    total_value = sum(i.price * i.stock for i in all_variants)
    
    #form for modal emppty
    form = VariantForm()               
    
    return render(request, 'admin/variant_management.html',{
        'product':product,
        'variants':variants,
        'form':form,
        'default_variant':default_variant,
        'total_stock':total_stock,
        'total_value':total_value,
        'query':q
    })
 

            
            
            
            
    
  