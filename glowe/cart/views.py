
from django.shortcuts import render, redirect, get_object_or_404
from product.models import Variant,Product
from .utils import get_user_cart
from .models import CartItem
from django.contrib import messages


def cart(request):
    if not request.user.is_authenticated:
        return redirect('signin')
    
    user_cart =get_user_cart(request.user)
    items= user_cart.items.select_related('variant__product')
    
    cart_items=[]
    total=0
    
    for item in items:
        variant=item.variant
        product=variant.product
        
        if product.is_active and  not product.is_deleted and variant.is_active:
            
            stock =variant.stock
            price=variant.price
            #out of stock  it marks akumm  out of stock ui 
            if stock == 0:
                cart_items.append({
                    'item':item,
                    'product':product,
                    'variant':variant,
                    'quantity':0,
                    'price':price,
                    'subtotal':0,
                    'stock':0,
                    'is_out_of_stock':True,
                    'low_stock':False,
                })
            else:
            
                # if selected more than stock
                if item.quantity > stock:
                    item.quantity = stock
                    item.save()
                
                qty =item.quantity
            
                subtotal =variant.price * qty
                total +=subtotal
                
                low_stock= stock > 0 and stock <=5
                
                cart_items.append({
                    'item':item,
                    'product':product,
                    'variant':variant,
                    'quantity':qty,
                    'price':price,
                    'subtotal':subtotal,
                    'stock':stock,
                    'is_out_of_stock':False,
                    'low_stock':low_stock,
                })
    is_empty= not cart_items
    
    cart_count=request.user.cart.items.count()
            
    return render(request, 'cart.html',{
        'cart_items':cart_items,
        'total':total,
        'is_empty':is_empty,
    })

def update_cart(request):
    if request.method == "POST":
        item_id=request.POST.get('item_id')
        
        try:
            quantity=int(request.POST.get('quantity',1))
        except:
            quantity =1
        #prevent 0 and neg
        if quantity <=0 :
            quantity=1
        
        item=get_object_or_404(CartItem,id=item_id,cart__user=request.user)
        variant = item.variant
        stock =variant.stock
        
        max_qty = 5
        
        if stock ==0 :
            item.quantity=0
            item.save()
            return redirect('cart')
        
        if quantity <= 0:
            item.delete()
            return redirect('cart')
        
        #if more than 
        if quantity > stock:
            quantity=stock
        
        if quantity > max_qty:
            quantity = max_qty
            
        item.quantity = quantity
        item.save()
    
    return redirect('cart') 

def remove_from_cart(request,item_id):
    if request.method =="POST":
        item = get_object_or_404(
            CartItem,id=item_id,cart__user=request.user)
        item.delete()
        messages.success(request, "Item removed from cart")
    return redirect('cart')