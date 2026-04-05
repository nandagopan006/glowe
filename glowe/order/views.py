from django.shortcuts import redirect, get_object_or_404,render
from django.contrib import messages
from django.db import transaction
from django.utils.crypto import get_random_string

from cart.models import Cart
from user.models import Address
from models import Order, OrderItem, ShippingAddress, Payment, OrderStatusHistory



def place_order(request):
    if request.method != "POST":
        return redirect('checkout')
     
    try :
        cart=request.user.cart
        cart_items=cart.items.select_related('variant','variant__product')
    except Cart.DoesNotExist:
        messages.error(request, "Cart not found")
        return redirect('cart')
    
    address_id = request.POST.get('address_id')
    address =get_object_or_404(Address,id =address_id,user=request.user)
    
    subtotal =0
    
    with transaction.atomic():
        for item in cart_items:
            variant=item.variant
            product=variant.product
            
            if not product.is_active:
                messages.error(request,f"{product.name} is unavailable")
                return redirect('cart')
            
            if not variant.is_active:
                messages.error(request,f"{product.name} is not available")
                return redirect('cart')
            
            if variant.stock == 0:
                messages.error(request,f"{product.name} is out of stock")
                return redirect('cart')
            
            if item.quantity == 0:
                messages.error(request,f"Only {variant.stock} left for {product.name}")
                return redirect('cart')
            
            if item.quantity > variant.stock:
                messages.error(request,f"{product.name} only {variant.stock} left")
                return redirect('cart')
            
            item.item_total = item.quantity * variant.price
            subtotal += item.item_total
            
        shipping = 0 if subtotal > 799 else 100
        total = subtotal + shipping
        
        order = Order.objects.create(user=request.user,
                                     order_number='ORD' + get_random_string(10).upper(),
                                     address=address,
                                     subtotal=subtotal,
                                     delivery_charge=shipping,
                                     discount_amount=0,
                                     total_amount=total,
                                    order_status="CONFIRMED"
                                     )
        
         #create order items + reduce stock
        for item in cart_items:
            variant=item.variant
            
            OrderItem.objects.create(
            order=order,
            variant=variant,
            price_at_time=variant.price,
            quantity=item.quantity)
            
            #reduce the stock
            variant.stock -= item.quantity
            variant.save()
        
        #save the ordered address
        ShippingAddress.objects.create(
        order=order,
        user=request.user,
        full_name=address.full_name,
        phone=address.phone_number,
        address_line1=address.street_address,
        city=address.city,
        district=address.district,
        state=address.state,
        country=address.country,
        pincode=address.pincode)
        
        #now only cod
        Payment.objects.create(
        order=order,
        payment_method="COD",
        amount=total,
        payment_status="PENDING")
        
        OrderStatusHistory.objects.create(
        order=order,
        status="CONFIRMED")
        
        
        cart_items.delete()
    
    messages.success(request,"Order placed successfully!")
    return redirect("order_success",order_id=order.id)
    