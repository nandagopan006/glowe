from django.shortcuts import get_object_or_404, render,redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import Wishlist
from product.models import Variant

@login_required
def toggle_wishlist(request, variant_id):
    
    if request.method != "POST":
        return redirect(request.META.get('HTTP_REFERER', 'wishlist'))
    
    variant = get_object_or_404(Variant,id=variant_id,is_active=True)
    
    if not variant.product.is_active or variant.product.is_deleted:
        messages.error(request, "Product not available")
        return redirect(request.META.get('HTTP_REFERER', 'wishlist'))
    
    wishlist_item =Wishlist.objects.filter(user=request.user,variant=variant)

    if wishlist_item.exists():
        wishlist_item.delete()
        messages.info(request, "Removed from wishlist")
    else:
        Wishlist.objects.create(user=request.user,variant=variant)
        messages.success(request,"Added to Wishlist")
    
    #for stay the same page(product detial/listing) thaneeahnn
    return redirect(request.META.get('HTTP_REFERER','wishlist'))


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
        
    




def wishlist_page(request):
    return render(request,"wishlist/wishlist.html")