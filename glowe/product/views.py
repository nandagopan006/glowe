from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import ProductForm,VariantForm
from .models import ProductImage,Product,Variant,Category
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator  
from django.db.models import Q,Sum,Min
from django.db.models import Prefetch
import json

def add_product(request):
    
    categories=Category.objects.filter(is_active=True, is_deleted=False)

    if request.method == "POST":
        form=ProductForm(request.POST)
        images=request.FILES.getlist('images')

        if form.is_valid():

            if len(images) < 3:
                messages.error(request,"Please upload at least 3 images")
                return render(request,'admin/add_product.html',{
                    'form':form,
                    'categories':categories})

            
            valid_types=['image/jpeg','image/png','image/webp','image/jpg']

            for img in images:
                if img.content_type not in valid_types:
                    messages.error(request,"Only JPG, PNG, WEBP allowed")
                    return render(request,'admin/add_product.html', {
                        'form':form,
                        'categories':categories})

                if img.size >2 *1024 *1024:
                    messages.error(request,"Each image must be under 2MB")
                    return render(request,'admin/add_product.html', {
                        'form':form,
                        'categories':categories})

            
            product = form.save()#for save product
            # Save images
            for i, img in enumerate(images):
                ProductImage.objects.create(
                    product=product,
                    image=img,
                    is_primary=(i ==0)  # first image = primary ak kumm
                )

            messages.success(request,"Product added successfully")
            return redirect('product_management')
    else:
        form=ProductForm()

    return render(request, 'admin/add_product.html',{
        'form': form,
        'categories': categories
    })
        
def edit_product(request, id):
    product = get_object_or_404(Product, id=id)
    categories = Category.objects.filter(is_active=True, is_deleted=False)

    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)
        images = request.FILES.getlist('images')
        is_active = request.POST.get('is_active') == 'true'
        primary_image_id = request.POST.get('primary_image_id', '').strip()

        if form.is_valid():
            # Count existing images + new ones 
            existing_count = product.images.count()
            new_count = len(images)
            total_images = existing_count + new_count

            if total_images < 3:
                messages.error(request, "Product must have at least 3 images.")
                return render(request, 'admin/edit_product.html', {
                    'form': form, 'product': product, 'categories': categories
                })

           
            valid_types = ['image/jpeg', 'image/png', 'image/webp', 'image/jpg']
            for img in images:
                if img.content_type not in valid_types:
                    messages.error(request, f"{img.name} is not a valid image type.")
                    return render(request, 'admin/edit_product.html', {
                        'form': form, 'product': product, 'categories': categories
                    })
                if img.size > 2 * 1024 * 1024:
                    messages.error(request, f"{img.name} must be under 2MB.")
                    return render(request, 'admin/edit_product.html', {
                        'form': form, 'product': product, 'categories': categories
                    })


            product = form.save(commit=False)
            product.is_active = is_active
            product.save()

        
            for img in images:
                ProductImage.objects.create(product=product, image=img, is_primary=False)

            #Set primary image if one was chosen
            if primary_image_id:
                product.images.update(is_primary=False)
                ProductImage.objects.filter(id=primary_image_id, product=product).update(is_primary=True)

            # Ensure at least one image is primary 
            if not product.images.filter(is_primary=True).exists():
                first = product.images.order_by('id').first()
                if first:
                    first.is_primary = True
                    first.save()

            messages.success(request, "Product updated successfully.")
            return redirect('product_management')

        else:
            # Form has errors – show them
            for errors in form.errors.values():
                for e in errors:
                    messages.error(request, e)

    else:
        form = ProductForm(instance=product)

    return render(request, 'admin/edit_product.html', {
        'form': form,
        'product': product,
        'categories': categories,
    })
    
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
        
        # Remove old primary
        product.images.update(is_primary=False)
        # and set new
        image.is_primary=True
        image.save()
        
        messages.success(request, "Primary image updated")
        return redirect('edit_product', id=product.id)
    
    
    return redirect('product_management')

def soft_delete_product(request,id):
    if request.method == "POST": 
    
        product=get_object_or_404(Product,id=id,is_deleted=False)
        product.is_deleted=True # soft delete 
        product.save()
        
        messages.success(request,"Product moved to archive")
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

def toggle_product_status(request,id):
    if request.method == "POST":
        product=get_object_or_404(Product, id=id)

        product.is_active =not product.is_active
        product.save()

        messages.success(request,"Product status updated")
        return redirect('product_management')

    return redirect('product_management')
    
def product_management(request): 
    
    q=request.GET.get('q','').strip()
    category=request.GET.get('category','')
    status=request.GET.get('status','live')
    active_status = request.GET.get('active_status','')
    products=Product.objects.all()
    
    if status =="archived":
        products=products.filter(is_deleted=True)
    else :
        products=products.filter(is_deleted=False)
    
    if active_status == "active":
        products = products.filter(is_active=True)
    elif active_status =="inactive":
             products = products.filter(is_active=False)
                
    if q :
        products=products.filter(
            Q(name__icontains=q)
        )
    
    if category :
        products=products.filter(category__id=category)
    
    products= products.prefetch_related('images','variants')
    
    paginator =Paginator(products.order_by('-id'), 5)
    page=request.GET.get('page')
    products =paginator.get_page(page)
    
    all_products =Product.objects.all()
    
    total_products=all_products.count()
    active_products=all_products.filter(is_active=True, is_deleted=False).count()
    archived_products=all_products.filter(is_deleted=True).count()
    
    for p in products :
        default_variant=p.variants.filter(is_default=True).first()
        p.display_price=default_variant.price if default_variant else 0
        
        p.total_stock= p.variants.aggregate(total=Sum('stock'))['total'] or 0
        
        primary_image=p.images.filter(is_primary=True).first()
        p.display_image =primary_image.image.url if primary_image and primary_image.image else None #primary_image is object and primary_image.image is file
        
    categories=Category.objects.all()
    
    return render(request,'admin/product_management.html',{
        'total_products':total_products,
        'active_products':active_products,
        'archived_products':archived_products,
        'products':products,
        'categories':categories,
        'query':q,
        'selected_category':category,
        'status':status,
        'active_status': active_status,
    })
    
def product_detail(request,id):
    product= get_object_or_404(Product,id=id,is_deleted=False)
    images=product.images.all()
    primary_image=images.filter(is_primary=True).first()
    
    variants=product.variants.filter(is_active=True)
    default_variant=variants.filter(is_default=True).first()
    
    base_price=default_variant.price if default_variant else 0
     
    total_stock= variants.aggregate(total=Sum('stock'))['total']or 0
    sku = default_variant.sku if default_variant else "N/A"
    stock_status='In Stock' if total_stock > 0 else "Out of Stock"
    variant_count=variants.filter(is_active=True).count() 
    low_stock=total_stock <10  
    skin_types_list = [s.strip() for s in product.skin_type.split(',')] if product.skin_type else []
    skin_types_list = [s.strip() for s in product.skin_type.split(',')] if product.skin_type else []
    how_to_use_steps = []
    if product.how_to_use:
        try:
            how_to_use_steps =json.loads(product.how_to_use)
        except:
            how_to_use_steps =[] 
        
    return render(request,'admin/product_detail.html',{
        'product':product,
        'images':images,
        'primary_image':primary_image,
        "variants":variants,
        "default_variant":default_variant,
        'base_price':base_price,
        'total_stock':total_stock,
        'sku':sku,
        'stock_status':stock_status,
        'variant_count':variant_count,
        'low_stock':low_stock,
        'skin_types_list':skin_types_list,
        'how_to_use_steps':how_to_use_steps,})
    
def add_variant(request,product_id):
    product = get_object_or_404(Product,id=product_id,is_deleted=False)
    
    if request.method =="POST":
        form=VariantForm(request.POST,initial={'product': product})
        
        if form.is_valid():
            variant=form.save(commit=False)
            variant.product = product
            
            
            user_active = request.POST.get('is_active') == 'True'
            if variant.stock == 0:
                variant.is_active = False
            else:
                variant.is_active = user_active
            
            
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
            
            user_active = request.POST.get('is_active') == 'True'
            if updated_variant.stock == 0:
                updated_variant.is_active = False
            else:
                updated_variant.is_active = user_active
            
            
            if variant.is_default:
                updated_variant.is_active = True
           #  if user select default remove other defaults
            if updated_variant.is_default :
                product.variants.exclude(id=variant.id).filter(is_default=True).update(is_default=False)
                          
             #if no default exists so that make this default
            if not product.variants.exclude(id=variant.id).filter(is_default=True).exists():
                updated_variant.is_default = True

            updated_variant.save()
            
            messages.success(request, "Variant updated successfully")
            return redirect('variant_management',product_id=product.id)

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
            if new_variant:
                new_variant.is_default=True
                new_variant.save()

        else:
            #Normal delete
            variant.delete()

        messages.success(request,"Variant deleted successfully")
        return redirect('variant_management',product_id=product.id)

    return redirect('product_management')

def toggle_variant_status(request, id):
    if request.method == "POST":
        variant = get_object_or_404(Variant, id=id)

        if variant.is_default:
            messages.error(request, 'Default variant cannot be disabled')
        else:
            # Prevent activating a variant with zero stock
            if not variant.is_active and variant.stock == 0:
                messages.error(request, 'Cannot activate a variant with zero stock.')
            else:
                variant.is_active = not variant.is_active
                variant.save()
                messages.success(request, "Variant status updated successfully.")

    return redirect('variant_management', product_id=variant.product.id)

def set_default_variant(request, id):
    variant = get_object_or_404(Variant, id=id)
    product = variant.product

    if request.method == "POST":

        if not variant.is_active:
            messages.error(request, "Cannot set inactive variant as default.")
            return redirect('variant_management', product_id=product.id)

        if variant.is_default:
            messages.info(request, "This is already the default variant.")
            return redirect('variant_management', product_id=product.id)

        product.variants.exclude(id=variant.id).update(is_default=False)

        variant.is_default = True
        variant.save()

        messages.success(request, f"{variant.size} set as default")

    return redirect('variant_management', product_id=product.id)

def variant_management(request,product_id):
    product=get_object_or_404(Product,id=product_id,is_deleted=False)
    status=request.GET.get('status','')
    #searchh
    q =request.GET.get('q','').strip()
    variants=product.variants.all()
    primary_image = product.images.filter(is_primary=True).first() or product.images.first()
   
    
    if q :
        variants =variants.filter(
            Q(size__icontains=q) | Q(sku__icontains=q)
        )
    if status =="active":
        variants =variants.filter(is_active=True)
    elif status =='inactive':
        variants=variants.filter(is_active=False) 
    
    variants=variants.order_by('id')
    paginator =Paginator(variants,4)
    page_number=request.GET.get('page')
    variants=paginator.get_page(page_number)       
    
    #Product summary
    all_variants=product.variants.all()
    default_variant=product.variants.filter(is_default=True).first()
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
        'query':q,
        'primary_image':primary_image,
    })
 

# --------------- end ---- admin side ayii --


#---== user side  statinggg--

def product_listing(request):
    
    products=Product.objects.filter(
        is_active=True,
        is_deleted=False,
        variants__is_active=True,
        variants__is_default=True, 
    ).distinct()
    
    
    search=request.GET.get('search','').strip()
    if search:
        products=products.filter(name__icontains=search) 
        
    category=request.GET.get('category','').strip()
    if category:
        products =products.filter(category__id=category)
    
    skin_type=request.GET.get('skin_type','').strip()
    if skin_type:
        products=products.filter(skin_type__iexact=skin_type)
        
    #price filtering     
    min_price=request.GET.get('min_price','').strip()
    max_price=request.GET.get('max_price','').strip()

    try:
        min_price = int(min_price) if min_price else None
        max_price = int(max_price) if max_price else None
    except ValueError:
        min_price = None
        max_price = None

    #if user mistake we correct it swap it 
    if min_price and max_price:
        if int(min_price) > int(max_price):
            min_price,max_price= max_price,min_price
            
    if min_price:
        products=products.filter(variants__price__gte=min_price)
    if max_price:
        products=products.filter(variants__price__lte=max_price)
    
    #sortingg
    sort=request.GET.get('sort','').strip()
    
    if sort == 'price_low':
        products=products.annotate(min_price=Min("variants__price")).order_by('min_price')
        
    elif sort == 'price_high':
        products=products.annotate(min_price=Min("variants__price")).order_by('-min_price')
        
    elif sort == 'a_z':
        products= products.order_by('name')
    
    elif sort == 'z_a':
        products =products.order_by('-name')
    
    else :
        products =products.order_by('-id')
        
    total_count = products.count()
        
    products =products.prefetch_related(
        Prefetch('images',queryset=ProductImage.objects.filter(is_primary=True)),#load only images  is is_primary=True
        Prefetch('variants',queryset=Variant.objects.filter(is_default=True)) # only the default true   appo load less fast kiitum 
    )

        
    paginator=Paginator(products,9)
    page_number=request.GET.get('page')
    page_obj=paginator.get_page(page_number)
    
    categories =Category.objects.filter(is_active=True,is_deleted=False)
    skin_types = ['Oily', 'Dry', 'Sensitive', 'Combination', 'Normal','Acnce-prono','Mature','Dehydrated','Dull']
    
    return render(request,"user/product_listing.html",{
        'page_obj':page_obj,
        "categories":categories,
        'total_count':total_count,
         'search_query':search,
        'selected_category':category,
        'selected_skin_type':skin_type,
        'selected_sort':sort,
        'min_price': min_price or 0,
        'max_price':max_price or 5000,
        'skin_types':skin_types,
    })
        

def product_detail_view(request,slug):
   
    product=get_object_or_404(
        Product.objects.prefetch_related('images', 'variants'),
        slug=slug,
        is_deleted=False
    )

    if not product.is_active:
        return redirect("product_listing")
    
    variants=product.variants.filter(is_active=True).order_by('size')
    
    if not variants.exists():
        return redirect('product_listing')

    variant_id=request.GET.get('variant')
    # get selected variant
    if variant_id:
        selected_variant=variants.filter(id=variant_id).first()
    else:
        selected_variant=None
    #If fallback.. to first variant
    if not selected_variant:
        selected_variant=variants.first()

    stock = selected_variant.stock if selected_variant else 0
    low_stock = stock if 0 < stock <= 5 else None
    all_out_of_stock =not variants.filter(stock__gt=0).exists()
    
    skin_type = product.skin_type if product.skin_type else "All Skin Types"
    description = product.description
    ingredients = product.ingredients
    how_to_use = product.how_to_use
    
    #not use now  ok appo venda
    delivery_info = "Free delivery in 3-5 days"
    
    images=product.images.all()
    
    related_products=Product.objects.filter(
        category=product.category,
        is_active=True,
        is_deleted=False
    ).exclude(id=product.id)[:4]
    
    return render(request,'user/product_detail_view.html',{
        'product':product,
        'variants':variants,
        'selected_variant': selected_variant,
        'stock':stock,                   
        'low_stock':low_stock,
        'all_out_of_stock':all_out_of_stock,
        'skin_type':skin_type,
        'description':description,
        'ingredients':ingredients,
        'how_to_use':how_to_use,
        'images':images,
        'related_products':related_products,
    })