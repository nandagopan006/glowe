from django.shortcuts import redirect, get_object_or_404,render
from django.contrib import messages
from .models import Order,OrderItem, ShippingAddress,Payment,OrderStatusHistory
from django.db import transaction
from django.utils.crypto import get_random_string
from product.models import Variant
from cart.models import Cart
from user.models import Address
from django.contrib.auth.decorators import login_required
from datetime import date, timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q
from django.core.paginator import Paginator





@login_required
def place_order(request):
    if request.method != "POST":
        return redirect('checkout')

    # prevent double order --   not allow dulpi oder
    if request.session.get('order_processing'):
        return redirect('cart')
    request.session['order_processing'] =True

    try :
        cart=request.user.cart
        cart_items=cart.items.select_related('variant','variant__product')
    except Cart.DoesNotExist:
        request.session['order_processing'] = False
        messages.error(request, "Cart not found")
        return redirect('cart')

    if not cart_items.exists():
        request.session['order_processing'] = False
        messages.error(request, "Cart is empty")
        return redirect('cart')

    address_id =request.POST.get('address_id')
    if not address_id:
        request.session['order_processing'] = False
        messages.error(request, "Please select a delivery address")
        return redirect('checkout')

    address =get_object_or_404(Address,id =address_id,user=request.user)

    subtotal =0

    with transaction.atomic():
        for item in cart_items:
            #lock variant ,,if one user bbuy same other USER aslo nedd lock  --oveerselling block
            variant = Variant.objects.select_for_update().get(id=item.variant.id)
            product=variant.product

            if not product.is_active:
                request.session['order_processing'] = False
                messages.error(request, f"{product.name} is unavailable")
                return redirect('cart')

            if not variant.is_active:
                request.session['order_processing'] = False
                messages.error(request, f"{product.name} is not available")
                return redirect('cart')

            if variant.stock == 0:
                request.session['order_processing'] = False
                messages.error(request, f"{product.name} is out of stock")
                return redirect('cart')

            if item.quantity > variant.stock:
                request.session['order_processing'] = False
                messages.error(request, f"{product.name}: only {variant.stock} left")
                return redirect('cart')

            item.item_total =item.quantity * variant.price
            subtotal += item.item_total

        shipping = 0 if subtotal > 999 else 100
        total =subtotal + shipping

        order =Order.objects.create(user=request.user,
            order_number='ORD-' + get_random_string(10).upper(),
            address=address,
            subtotal=subtotal,
            delivery_charge=shipping,
            discount_amount=0,
            total_amount=total,
            order_status=Order.Status.CONFIRMED
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
        status=Order.Status.CONFIRMED)
        
       
        send_mail(
            subject="Order Confirmed 🛍️",
            
            message=f"""
        Hi {request.user.username},

        Your order has been placed successfully!

        Order ID: {order.order_number}
        Total Amount: ₹{order.total_amount}

        We will deliver your order soon 🚚
        
        ━━━━━━━━━━━━━━━━━━━━━━━
        What Happens Next?
        ━━━━━━━━━━━━━━━━━━━━━━━
        • Your order is being processed  
        • It will be carefully packed and shipped  
        • Delivery will be completed within 3–7 business days  

        You will receive further updates as your order progresses.

                Thank you for shopping with us ❤️
                """,

            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[request.user.email],
            fail_silently=True,
        )

        #dlt all item, frm crt
        cart_items.delete()

    #for geting the current
    request.session['last_order_id'] = order.id

    request.session['order_processing'] = False
    messages.success(request,"Order placed successfully!")
    return redirect('order_success',order_id=order.id)

@login_required
def order_success(request,order_id):
    #get order the user
    order= get_object_or_404(Order,id=order_id,user=request.user)
    
    #onlyy the now done order
    last_order_id =request.session.get('last_order_id')
    if last_order_id !=order.id:
        return redirect('home')
    
    #get all items this order
    order_items = order.items.select_related('variant','variant__product')
    
    # direct access not not alllow  like not place order
    if not order_items.exists():
        return redirect('home')
    
    order_date = order.created_at.date()
    delivery_start=order_date + timedelta(days=3)
    delivery_end=order_date + timedelta(days=7)
    
    # get payment info
    try:
        payment = order.payment
    except Payment.DoesNotExist:
        return redirect('home')

    return render(request,'user/order_success.html',{
        "order":order,
        "order_items":order_items,
        "delivery_start":delivery_start,
        "delivery_end":delivery_end,
        "payment":payment,
    })
    
@login_required 
def order_listing(request):
    orders=Order.objects.filter(user=request.user).prefetch_related('items__variant__product__images')
    
    orders=orders.order_by('-created_at')
    
    search=request.GET.get('search','').strip()
    if search :
        orders=orders.filter( Q(order_number__icontains=search) |
         Q(items__variant__product__name__icontains=search)).distinct()
    
    filter_by=request.GET.get('filter','6m')
    
    now =timezone.now()
    
    if filter_by =='1w':
        orders=orders.filter(created_at__gte=now -timedelta(weeks=1))
    elif filter_by =='1m' :
        orders=orders.filter(created_at__gte=now -timedelta(days=30))
    elif filter_by == '3m':
        orders=orders.filter(created_at__gte=now-timedelta(days=90))
    elif filter_by == '6m':
        orders=orders.filter(created_at__gte=now- timedelta(days=180))
    elif filter_by == '1y':
        orders=orders.filter(created_at__gte=now- timedelta(days=365))
    
    for order in orders :
        order.delivery_start =order.created_at +timedelta(days=3)
        order.delivery_end =order.created_at +timedelta(days=7)
        
    total_orders=orders.count()
    paginator=Paginator(orders,5)
    page=request.GET.get('page')
    orders=paginator.get_page(page)    
        
    return render(request,'user/order_listing.html',{
        'orders':orders,
        'search':search,
        'filter_by':filter_by,
        'total_orders':total_orders,
    })
    
        
@login_required
def order_detial(request,order_id):
    order=get_object_or_404(Order,id=order_id,user=request.user)
    order_items =order.items.select_related('variant__product')
    
    order.delivery_start=order.created_at + timedelta(days=3)
    order.delivery_end = order.created_at + timedelta(days=7)

    # Tracking history
    history =order.status_history.all().order_by('-updated_at')

    #cancel not in this
    can_cancel=order.order_status in [
        Order.Status.PENDING,
        Order.Status.CONFIRMED,
        Order.Status.PROCESSING,
    ]
    #return allowed
    can_return = order.order_status == Order.Status.DELIVERED
    
    # payment
    payment = getattr(order,'payment',None)
    
    total_count=order_items.count()
    
    
    return render(request,'user/order_detail.html', {
        'order':order,
        'order_items':order_items,
        'history':history,
        'delivery_start':order.delivery_start,
        'delivery_end':order.delivery_end,
        'can_cancel':can_cancel,
        'can_return':can_return,
        'payment':payment,
        'total_count':total_count
        
    })
