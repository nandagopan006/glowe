
from django.shortcuts import render, redirect, get_object_or_404
from .utils import get_user_cart
from .models import CartItem, Cart
from user.models import Address
from django.contrib import messages
from coupons.views import calculate_discount
from coupons.models import Coupon
from django.utils import timezone
from decimal import Decimal
from wallet.models import Wallet
from offer.utils import get_best_offer
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache

@login_required
def cart(request):
    user_cart =get_user_cart(request.user)
    items= user_cart.items.select_related('variant__product')
    
    cart_items=[]
    total=Decimal('0.00')
    total_offer_savings = Decimal('0.00')
    
    for item in items:
        variant=item.variant
        product=variant.product
        
        if product.is_active and  not product.is_deleted and variant.is_active:
            
            stock =variant.stock
            
            try:
                price = Decimal(str(variant.price))
                offer, discount_per_unit = get_best_offer(product, price)
                if offer:
                    if discount_per_unit > price:
                        discount_per_unit = price
                    item_final_price = price - discount_per_unit
                    if item_final_price < Decimal("0.00"):
                        item_final_price = Decimal("0.00")
                    item_has_offer = True
                    item_discount = discount_per_unit
                    if offer.discount_type == "PERCENTAGE":
                        item_offer_text = f"{offer.discount_value:g}% OFF"
                    else:
                        item_offer_text = f"Flat ₹{offer.discount_value:g} OFF"
                else:
                    item_final_price = price
                    item_has_offer = False
                    item_discount = Decimal("0.00")
                    item_offer_text = ""
            except Exception:
                item_final_price = Decimal(str(variant.price))
                item_has_offer = False
                item_discount = Decimal("0.00")
                item_offer_text = ""
            
            #out of stock  it marks akumm  out of stock ui 
            if stock == 0:
                cart_items.append({
                    'item':item,
                    'product':product,
                    'variant':variant,
                    'quantity':0,
                    'price':price,
                    'final_price': item_final_price,
                    'subtotal':Decimal('0.00'),
                    'stock':0,
                    'is_out_of_stock':True,
                    'low_stock':False,
                    'has_offer': item_has_offer,
                    'discount': item_discount,
                    'offer_text': item_offer_text,
                })
            else:
            
                # if selected more than stock
                if item.quantity > stock:
                    item.quantity = stock
                    item.save()
                
                qty =item.quantity
            
                subtotal = item_final_price * qty
                total +=subtotal
                total_offer_savings += item_discount * qty
                
                low_stock= stock > 0 and stock <=5
                
                cart_items.append({
                    'item':item,
                    'product':product,
                    'variant':variant,
                    'quantity':qty,
                    'price':price,
                    'final_price': item_final_price,
                    'subtotal':subtotal,
                    'stock':stock,
                    'is_out_of_stock':False,
                    'low_stock':low_stock,
                    'has_offer': item_has_offer,
                    'discount': item_discount,
                    'offer_text': item_offer_text,
                })
    is_empty = not cart_items
    cart_count = request.user.cart.items.count()
            
    return render(request, 'cart.html',{
        'cart_items':cart_items,
        'total':total,
        'is_empty':is_empty,
        'cart_count':cart_count,
        'total_offer_savings': total_offer_savings.quantize(Decimal("0.01")),
    })

@login_required
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
        stock = variant.stock
        max_qty = 5
        
        if stock == 0:
            item.quantity = 0
            item.save()
            return redirect('cart')
        
        if quantity > stock:
            quantity=stock
        
        if quantity > max_qty:
            quantity = max_qty
            
        item.quantity = quantity
        item.save()
    
    return redirect('cart') 

@login_required
def remove_from_cart(request, item_id):
    if request.method == "POST":
        item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        item.delete()
        messages.success(request, "Item removed from cart")
    return redirect('cart')


@never_cache
@login_required
def checkout(request):
    
    try :
        cart =request.user.cart
        cart_items =cart.items.select_related('variant','variant__product').all()
    except Cart.DoesNotExist:
        messages.error(request,"Cart not found")
        return redirect('cart')
    
    addresses = Address.objects.filter(user=request.user)
    
    #chck cart is empty
    if not cart_items.exists():
        messages.error(request, "Your cart is empty")
        return redirect('cart')
    
    default_address =addresses.filter(is_default=True).first()
    
    if not default_address:
        default_address=addresses.first()
        
    subtotal = Decimal('0.00')
    original_subtotal = Decimal('0.00')
    total_offer_savings = Decimal('0.00')
    checkout_items = []
    
    for item in cart_items:
        variant = item.variant
        product = variant.product
        
        if not product.is_active or product.is_deleted:
            messages.error(request, f"{product.name} is unavailable")
            return redirect('cart')

        if not variant:
            messages.error(request, "Product not found")
            return redirect('cart')
        
        if not variant.is_active:
            messages.error(request, f"{product.name} is not available")
            return redirect('cart')
        
        if variant.stock == 0:
            messages.error(request, f"{product.name} is out of stock")
            return redirect('cart')
            
        if item.quantity > variant.stock:
            messages.error(request, f"{product.name} only {variant.stock} left")
            return redirect('cart')
    
        try:
            price = Decimal(str(variant.price))
            original_subtotal += price * item.quantity
            offer, offer_disc = get_best_offer(product, price)
            if offer:
                if offer_disc > price:
                    offer_disc = price
                item_final_price = price - offer_disc
                if item_final_price < Decimal("0.00"):
                    item_final_price = Decimal("0.00")
                item_has_offer = True
                item_discount = offer_disc
                if offer.discount_type == "PERCENTAGE":
                    item_offer_text = f"{offer.discount_value:g}% OFF"
                else:
                    item_offer_text = f"Flat ₹{offer.discount_value:g} OFF"
            else:
                item_final_price = price
                item_has_offer = False
                item_discount = Decimal("0.00")
                item_offer_text = ""
        except Exception:
            item_final_price = Decimal(str(variant.price))
            original_subtotal += item_final_price * item.quantity
            item_has_offer = False
            item_discount = Decimal("0.00")
            item_offer_text = ""
        
        item.item_total = item_final_price * item.quantity
        item.original_total = price * item.quantity
        item.final_price = item_final_price
        item.original_price = price
        item.has_offer = item_has_offer
        item.offer_discount = item_discount
        item.offer_text = item_offer_text
        
        subtotal += Decimal(item.item_total)
        total_offer_savings += item_discount * item.quantity
        
    shipping = Decimal('0.00') if subtotal > Decimal('999') else Decimal('100.00')
    
    # check any coupon apply
    discount = calculate_discount(request, subtotal)
    
    # Get available coupons
    today = timezone.now().date()
    available_coupons = Coupon.objects.filter(
        is_active=True,
        is_deleted=False,
        start_date__lte=today,
        end_date__gte=today
    )
    
    wallet, _ = Wallet.objects.get_or_create(user=request.user)

    
    final_total = subtotal + shipping - discount
    if final_total < 0:
        final_total = Decimal('0.00')
    
    return render(request, "checkout.html", {
        "cart_items": cart_items,
        "addresses": addresses,
        "default_address": default_address,
        "subtotal": subtotal,
        "original_subtotal": original_subtotal.quantize(Decimal("0.01")),
        "shipping": shipping,
        "discount": discount,
        "final_total": final_total,
        "available_coupons": available_coupons,
        "wallet":wallet,
        "total_offer_savings": total_offer_savings.quantize(Decimal("0.01")),
    })