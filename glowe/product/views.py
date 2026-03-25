from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import ProductForm
from .models import ProductImage,Product,Variant
from django.shortcuts import get_object_or_404


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

def set_primary_image(request,id):
    image=get_object_or_404(ProductImage,id=id)
    product=image.product
    
    if image.is_primary:
        messages.info(request,"Already primary image")
        return redirect('edit_product',id=product.id)
    
    Product.images.update(is_primary=False)
    
    image.is_primary=True
    image.save()
    
    messages.info(request, "Already primary image")
    return redirect('edit_product', id=product.id)

def delete_product(request,id):
    product=get_object_or_404(Product,id=id)
    product.is_deleted=True
    product.save()
    
    messages.success(request,"Product deleted successfully")
    return redirect('product_management')
    
    

