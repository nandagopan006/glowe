from django.shortcuts import get_object_or_404, render,redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import Wishlist
from product.models import Variant
from cart.models import Cart,CartItem
from cart.utils import get_user_cart
from .models import StockNotification
from django.db.models import Min

@login_required
def toggle_wishlist(request, variant_id):
    
    if request.method != "POST":
        return redirect(request.META.get('HTTP_REFERER','wishlist'))
    
    variant = get_object_or_404(Variant,id=variant_id,is_active=True)
    
    if not variant.product.is_active or variant.product.is_deleted:
        messages.error(request, "Product not available")
        return redirect(request.META.get('HTTP_REFERER','wishlist'))
    
    wishlist_item = Wishlist.objects.filter(user=request.user, variant=variant)

    if wishlist_item.exists():
        wishlist_item.delete()
        status = "removed"
        message = "Removed from wishlist"
    else:
        Wishlist.objects.create(user=request.user, variant=variant)
        status = "added"
        message = "Added to Wishlist"

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"status": status, "message": message})

    if status == "added":
        messages.success(request, message)
    else:
        messages.info(request, message)

    return redirect(request.META.get("HTTP_REFERER", "wishlist"))


@login_required
def remove_from_wishlist(request, variant_id):
    
    if request.method != "POST":
        return redirect('wishlist')
    
    variant=get_object_or_404(Variant,id=variant_id)
    
    wishlist_item=Wishlist.objects.filter(user=request.user,variant=variant).first()
    
    if wishlist_item:
        wishlist_item.delete()
        messages.success(request,"Item removed from wishlist")
    else:
        messages.warning(request, "Item not found")
        
    return redirect("wishlist")

@login_required     
def wishlist_page(request):
    
    wishlist_items=Wishlist.objects.filter(
        user=request.user).select_related('variant','variant__product')
    # order sort
    wishlist_items =wishlist_items.order_by('-created_at')
    
    wishlist_count=wishlist_items.count()
    
    # exclude products already in wishlist (all variants of those products)
    wishlisted_product_ids=wishlist_items.values_list('variant__product_id',flat=True)
    
    # get one variant per product (default variant or first) using distinct product
    
    one_variant_ids=Variant.objects.filter(
        is_active=True,product__is_active=True,
        product__is_deleted=False,
    ).exclude(product_id__in=wishlisted_product_ids).values('product_id').annotate(
        first_variant=Min('id')
    ).values_list('first_variant',flat=True)
    
    recommend_products=Variant.objects.filter(
        id__in=one_variant_ids
    ).select_related('product').prefetch_related('product__images')[:8]
    
    return render(request,"wishlist/wishlist.html",{
        'wishlist_items':wishlist_items,
        'wishlist_count':wishlist_count,
        'recommend_products':recommend_products,
    })
@login_required
def clear_wishlist(request) :
    
    if request.method=="POST":
        Wishlist.objects.filter(user=request.user).delete()
    
    return redirect("wishlist")

@login_required
def move_to_cart(request,variant_id):
    
    if request.method != "POST":
        return redirect('wishlist')
    
    
    variant =get_object_or_404(Variant,id=variant_id,is_active=True)
    
    # just checking product active false or delete ayo inn nokkuumm 
    if not variant.product.is_active or variant.product.is_deleted:
        messages.error(request,"Product not available")
        return redirect('wishlist')
    if variant.stock == 0:
        messages.warning(request,"Out of stock")
        return redirect('wishlist')
    
    cart = get_user_cart(request.user)
    
    #check if item already in cart
    cart_item=CartItem.objects.filter(
        cart=cart,variant=variant
    ).first()
    
    max_limit=5
    
    if cart_item:#if already increase the qty & and only if not morethan the maxqty
        
        if cart_item.quantity >= max_limit:# if already have 5 qty to allow
            messages.warning(request, f"You can only add {max_limit} items . You Already Have The Max Quantity Items")
            return redirect('wishlist')
            
        if cart_item.quantity >= variant.stock :
            messages.warning(request,'Maximum stock reached ')
            return redirect('wishlist')
        
        cart_item.quantity+=1
        cart_item.save()
    else:# to crerate new item
        CartItem.objects.create(cart=cart,variant=variant,quantity=1)
    
    Wishlist.objects.filter(user=request.user,variant=variant).delete() # pinne dlte karo hahha
    
    messages.success(request,"Added to cart")
    return redirect('wishlist')

@login_required
def notify_me(request,variant_id):
    if request.method !="POST":
        return redirect('wishlist')
    
    variant = get_object_or_404(Variant,id=variant_id)
    
    if variant.stock > 0 :
        messages.info(request,"Product already in stock")
        return redirect('wishlist')
        
    obj, created=StockNotification.objects.get_or_create(
        user=request.user,variant=variant)
    
    if created :
        messages.success(request, "You will be notified when product is back ")
    else:
        messages.info(request, "You already requested notification")
        
    return redirect('wishlist')
    
    
    


