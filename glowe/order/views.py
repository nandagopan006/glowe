from django.shortcuts import redirect, get_object_or_404, render
from django.contrib import messages
from order.models import Order, OrderItem, ShippingAddress, Payment, OrderStatusHistory
from django.db import transaction
from django.utils.crypto import get_random_string
from product.models import Variant
from cart.models import Cart
from user.models import Address
from django.contrib.auth.decorators import login_required
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import io
from collections import defaultdict



@login_required
def place_order(request):
    if request.method != "POST":
        return redirect("checkout")

    # prevent double order --   not allow dulpi oder
    if request.session.get("order_processing"):
        return redirect("cart")
    request.session["order_processing"] = True

    try:
        cart = request.user.cart
        cart_items = cart.items.select_related("variant", "variant__product")
    except Cart.DoesNotExist:
        request.session["order_processing"] = False
        messages.error(request, "Cart not found")
        return redirect("cart")

    if not cart_items.exists():
        request.session["order_processing"] = False
        messages.error(request, "Cart is empty")
        return redirect("cart")

    address_id = request.POST.get("address_id")
    if not address_id:
        request.session["order_processing"] = False
        messages.error(request, "Please select a delivery address")
        return redirect("checkout")

    address = get_object_or_404(Address, id=address_id, user=request.user)

    subtotal = 0

    with transaction.atomic():
        for item in cart_items:
            # lock variant ,,if one user bbuy same other USER aslo nedd lock  --oveerselling block
            variant = Variant.objects.select_for_update().get(id=item.variant.id)
            product = variant.product

            if not product.is_active:
                request.session["order_processing"] = False
                messages.error(request, f"{product.name} is unavailable")
                return redirect("cart")

            if not variant.is_active:
                request.session["order_processing"] = False
                messages.error(request, f"{product.name} is not available")
                return redirect("cart")

            if variant.stock == 0:
                request.session["order_processing"] = False
                messages.error(request, f"{product.name} is out of stock")
                return redirect("cart")

            if item.quantity > variant.stock:
                request.session["order_processing"] = False
                messages.error(request, f"{product.name}: only {variant.stock} left")
                return redirect("cart")

            item.item_total = item.quantity * variant.price
            subtotal += item.item_total

        shipping = 0 if subtotal > 999 else 100
        total = subtotal + shipping

        order = Order.objects.create(
            user=request.user,
            order_number="ORD-" + get_random_string(10).upper(),
            address=address,
            subtotal=subtotal,
            delivery_charge=shipping,
            discount_amount=0,
            total_amount=total,
            order_status=Order.Status.CONFIRMED,
        )

        # create order items + reduce stock
        for item in cart_items:
            variant = item.variant

            OrderItem.objects.create(
                order=order,
                variant=variant,
                price_at_time=variant.price,
                quantity=item.quantity,
            )

            # reduce the stock
            variant.stock -= item.quantity
            variant.save()

        # save the ordered address
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
            pincode=address.pincode,
        )

        # now only cod
        Payment.objects.create(
            order=order, payment_method="COD", amount=total, payment_status="PENDING"
        )

        OrderStatusHistory.objects.create(order=order, status=Order.Status.CONFIRMED)

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

        # dlt all item, frm crt
        cart_items.delete()

    # for geting the current
    request.session["last_order_id"] = order.id

    request.session["order_processing"] = False
    messages.success(request, "Order placed successfully!")
    return redirect("order_success", order_id=order.id)


@login_required
def order_success(request, order_id):
    # get order the user
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # onlyy the now done order
    last_order_id = request.session.get("last_order_id")
    if last_order_id != order.id:
        return redirect("home")

    # get all items this order
    order_items = order.items.select_related("variant", "variant__product")

    # direct access not not alllow  like not place order
    if not order_items.exists():
        return redirect("home")

    order_date = order.created_at.date()
    delivery_start = order_date + timedelta(days=3)
    delivery_end = order_date + timedelta(days=7)

    # get payment info
    try:
        payment = order.payment
    except Payment.DoesNotExist:
        return redirect("home")

    return render(
        request,
        "user/order_success.html",
        {
            "order": order,
            "order_items": order_items,
            "delivery_start": delivery_start,
            "delivery_end": delivery_end,
            "payment": payment,
        },
    )


@login_required
def order_listing(request):
    orders = Order.objects.filter(user=request.user).prefetch_related(
        "items__variant__product__images"
    )

    orders = orders.order_by("-created_at")

    search = request.GET.get("search", "").strip()
    if search:
        orders = orders.filter(
            Q(order_number__icontains=search)
            | Q(items__variant__product__name__icontains=search)
        ).distinct()

    filter_by = request.GET.get("filter", "6m")

    now = timezone.now()

    if filter_by == "1w":
        orders = orders.filter(created_at__gte=now - timedelta(weeks=1))
    elif filter_by == "1m":
        orders = orders.filter(created_at__gte=now - timedelta(days=30))
    elif filter_by == "3m":
        orders = orders.filter(created_at__gte=now - timedelta(days=90))
    elif filter_by == "6m":
        orders = orders.filter(created_at__gte=now - timedelta(days=180))
    elif filter_by == "1y":
        orders = orders.filter(created_at__gte=now - timedelta(days=365))

    for order in orders:
        order.delivery_start = order.created_at + timedelta(days=3)
        order.delivery_end = order.created_at + timedelta(days=7)
        
        # cancelled items  the item count or create duplicate images
        active = [item for item in order.items.all() if item.item_status != 'CANCELLED']
        order.display_items = active if active else list(order.items.all())
        
    total_orders = orders.count()
    paginator = Paginator(orders, 5)
    page = request.GET.get("page")
    orders = paginator.get_page(page)

    return render(
        request,
        "user/order_listing.html",
        {
            "orders": orders,
            "search": search,
            "filter_by": filter_by,
            "total_orders": total_orders,
        },
    )


@login_required
def order_detial(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # not cancelled item
    active_items =order.items.exclude(item_status=OrderItem.Status.CANCELLED).select_related("variant__product").prefetch_related("variant__product__images")

    cancelled_items =order.items.filter(item_status=OrderItem.Status.CANCELLED).select_related("variant__product").prefetch_related("variant__product__images")

    
    grouped = {}
    for item in cancelled_items:
        variant_id = item.variant_id

        if variant_id not in grouped:
            
            grouped[variant_id] = {
                'variant': item.variant,
                'price_at_time': item.price_at_time,
                'quantity': item.quantity,
                'cancel_reason': item.cancel_reason,
            }
        else:
            # Same variant + new
            grouped[variant_id]['quantity'] += item.quantity

    # Convert to a simple list
    cancelled_items = list(grouped.values())

    # Step 5: Check if ALL items are cancelled
    all_cancelled = not active_items.exists()

    order.delivery_start = order.created_at + timedelta(days=3)
    order.delivery_end = order.created_at + timedelta(days=7)

    history = order.status_history.all().order_by("-updated_at")

    can_cancel = order.order_status in [
        Order.Status.PENDING,
        Order.Status.CONFIRMED,
        Order.Status.PROCESSING,
    ]
    can_return = order.order_status == Order.Status.DELIVERED
    payment = getattr(order, "payment", None)
  
    # cancelled_items is a Python list so use len(), not .count()
    if all_cancelled:
        total_count = len(cancelled_items)
    else:
        total_count = active_items.count()


    return render(request, "user/order_detail.html", {
        "order": order,
        "active_items": active_items,
        "cancelled_items": cancelled_items,
        "all_cancelled": all_cancelled,
        "history": history,
        "delivery_start": order.delivery_start,
        "delivery_end": order.delivery_end,
        "can_cancel": can_cancel,
        "can_return": can_return,
        "payment": payment,
        "total_count": total_count,
    })



@login_required
def cancel_order(request, order_id):

    if request.method != "POST":
        return redirect("order_detail", order_id=order_id)

    order = get_object_or_404(Order, id=order_id, user=request.user)

    # chck allowed only
    if order.order_status not in [
        Order.Status.PENDING,
        Order.Status.CONFIRMED,
        Order.Status.PROCESSING,
    ]:

        messages.error(request, "Order cannot be cancelled")
        return redirect("order_detail", order_id=order.id)

    if order.order_status == Order.Status.CANCELLED:
        messages.error(request, "Already cancelled")
        return redirect("order_detail", order.id)

    reason = request.POST.get("reason", "")

    with transaction.atomic():
        for item in order.items.filter(~Q(item_status=OrderItem.Status.CANCELLED)):
            variant = item.variant
            variant.stock += item.quantity
            variant.save()

            item.item_status = OrderItem.Status.CANCELLED
            item.cancel_reason = reason
            item.save()

        # Update order status but preserve the original total price for record-keeping
        order.order_status = Order.Status.CANCELLED
        order.save()

    # histy
    OrderStatusHistory.objects.create(order=order, status=Order.Status.CANCELLED)
    send_mail(
        subject="Order Cancelled ❌",
        message=f"""
Hi {request.user.full_name},

Your order has been cancelled successfully.

Order ID: {order.order_number}

If payment was made, refund will be processed shortly.

Thank you ❤️
""",
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[request.user.email],
        fail_silently=True,
    )

    messages.success(request, "Order cancelled successfully")
    return redirect("order_cancelled_success", order_id=order.id)


@login_required
def cancel_order_item(request, item_id):

    if request.method != "POST":
        return redirect("home")

    item = get_object_or_404(OrderItem, id=item_id, order__user=request.user)

    order = item.order

    if order.order_status not in [
        Order.Status.PENDING,
        Order.Status.CONFIRMED,
        Order.Status.PROCESSING,
    ]:

        messages.error(request, "cannot cancel this item")
        return redirect("order_detail", order_id=order.id)

    if item.item_status == OrderItem.Status.CANCELLED:
        messages.error(request, "Item Already cancelled")
        return redirect("order_detail", order.id)

    reason = request.POST.get("reason", "")
    try:
        quantity_to_cancel = int(request.POST.get("quantity", item.quantity))
    except (ValueError, TypeError):
        quantity_to_cancel = item.quantity

    if quantity_to_cancel > item.quantity or quantity_to_cancel <= 0:
        messages.error(request, "Invalid quantity")
        return redirect("order_detail", order_id=order.id)

    with transaction.atomic():
        # Restore stock for the cancelled portion
        variant = item.variant
        variant.stock += quantity_to_cancel
        variant.save()

        # Update order subtotal
        cancelled_amount = item.price_at_time * quantity_to_cancel
        order.subtotal -= cancelled_amount

        # If partial cancellation
        if quantity_to_cancel < item.quantity:
            # Reduce original item quantity
            item.quantity -= quantity_to_cancel
            item.save()

            # Create a new record for the cancelled units
            OrderItem.objects.create(
                order=order,
                variant=item.variant,
                price_at_time=item.price_at_time,
                quantity=quantity_to_cancel,
                item_status=OrderItem.Status.CANCELLED,
                cancel_reason=reason,
            )
        else:
            # Full item cancellation
            item.item_status = OrderItem.Status.CANCELLED
            item.cancel_reason = reason
            item.save()

        # Correctly recalculate total
        order.total_amount = order.subtotal + order.delivery_charge
        order.save()

        # Log history
        OrderStatusHistory.objects.create(order=order, status="ITEM_CANCELLED")

        # Check if all items in the order are now cancelled
        all_cancelled = not order.items.filter(
            ~Q(item_status=OrderItem.Status.CANCELLED)
        ).exists()
        if all_cancelled:
            order.order_status = Order.Status.CANCELLED
            order.save()

    send_mail(
        subject="Item Cancelled ❌",
        message=f"""
Hi {request.user.username},

One item from your order has been cancelled.

Order ID: {order.order_number}

Refund will be processed shortly.

Thank you ❤️
""",
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[request.user.email],
        fail_silently=True,
    )

    messages.success(request, "Item cancelled succussfully")
    return redirect("order_cancelled_success", order_id=order.id)


@login_required
def order_cancelled_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Get all cancelled items for this order
    cancelled_items = order.items.filter(item_status=OrderItem.Status.CANCELLED).select_related(
        "variant__product"
    )

    if not cancelled_items.exists():
        return redirect("order_detail", order_id=order_id)

    # Determine if the entire order is cancelled
    total_items = order.items.count()
    full_cancelled = (cancelled_items.count() == total_items)
    
    cancellation_id = f"CNCL-{str(order.id).zfill(5)}"
    
    # Get payment method info
    payment = getattr(order, 'payment', None)

    return render(
        request,
        "user/order_cancelled.html",{
            "order": order,
            "cancelled_items":cancelled_items,
            "cancellation_id":cancellation_id,
            "payment": payment,})

@login_required
def download_invoice(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    addr = order.shipping_address
    pay = getattr(order, 'payment', None)

    styles = getSampleStyleSheet()
    B = lambda t: Paragraph(f"<b>{t}</b>", styles["Normal"])
    N = lambda t: Paragraph(str(t), styles["Normal"])
    INR = lambda v: f"Rs.{v:,.2f}"

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=30, bottomMargin=30)

    meta = Table([[B("Glowe"), B(f"INVOICE # {order.order_number}")]], colWidths=[270, 270])
    meta.setStyle(TableStyle([("ALIGN", (1, 0), (1, 0), "RIGHT")]))

    info = Table([
        [B("Bill To"),                    B("Ship To"),          B("Payment")],
        [N(order.user.get_full_name()),   N(addr.full_name),     N(pay.payment_method if pay else "—")],
        [N(order.user.email),             N(addr.address_line1), N(pay.payment_status if pay else "—")],
        ["",                              N(f"{addr.city}, {addr.state} {addr.pincode}"), ""],
        ["",                              N(addr.country),       ""],
    ], colWidths=[180, 180, 180])
    info.setStyle(TableStyle([
        ("FONTNAME",  (0, 0), (-1, 0), "Helvetica-Bold"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.black),
        ("FONTSIZE",  (0, 0), (-1, -1), 9),
        ("VALIGN",    (0, 0), (-1, -1), "TOP"),
    ]))

    # Group items by variant
    grouped = defaultdict(lambda: {"name": "", "qty": 0, "price": 0})
    for item in order.items.all():
        key = item.variant.id
        grouped[key]["name"]  = item.variant.product.name[:50]
        grouped[key]["price"] = item.price_at_time
        grouped[key]["qty"]  += item.quantity

    # Build item rows
    rows = [["Product", "Qty", "Unit Price", "Amount"]]
    for g in grouped.values():
        qty = g["qty"]
        price = g["price"]
        rows.append([
            g["name"],
            qty,
            INR(price),
            INR(qty * price),
        ])

    # Compute totals from actual line items (not stale order fields)
    computed_subtotal = sum(g["qty"] * g["price"] for g in grouped.values())
    computed_total = computed_subtotal + order.delivery_charge

    rows += [
        ["", "", "Subtotal", INR(computed_subtotal)],
        ["", "", "Shipping", INR(order.delivery_charge)],
        ["", "", B("Total"), B(INR(computed_total))],
    ]

    table = Table(rows, colWidths=[300, 60, 80, 100])
    table.setStyle(TableStyle([
        ("FONTNAME",       (0, 0),  (-1, 0),  "Helvetica-Bold"),
        ("BACKGROUND",     (0, 0),  (-1, 0),  colors.black),
        ("TEXTCOLOR",      (0, 0),  (-1, 0),  colors.white),
        ("ALIGN",          (1, 0),  (-1, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1),  (-1, -1), [colors.whitesmoke, colors.white]),
        ("LINEABOVE",      (0, -3), (-1, -3), 0.5, colors.grey),
        ("FONTSIZE",       (0, 0),  (-1, -1), 9),
    ]))

    doc.build([meta, Spacer(1, 8), info, Spacer(1, 16), table])
    buf.seek(0)
    res = HttpResponse(buf, content_type="application/pdf")
    res["Content-Disposition"] = f'attachment; filename="invoice_{order.order_number}.pdf"'
    return res











#-------- end user side ---- -- -- - - - - - ok


#--start ---admin side---- - - - - - -------


@login_required
def admin_order_list(request):
    
    order=Order.objects.select_related('user').all()
    order=order.order_by('-created_at')
    
    search =request.GET.get('search','').strip()
    
    if search :
        orders=orders.filter(Q (order_number__icontains=search) | 
                             Q (user__full_name__icontains=search))
        
        
    status =request.GET.get('status','')
    if status :
        orders =orders.filter(order_status=status)
    
    filter_by =request.GET.get('filter','all')
    
    if filter_by == 'pending':
        orders=orders.filter(order_status=Order.Status.PENDING)
        
    elif filter_by == 'confirmed':
        orders =orders.filter(order_status=Order.Status.CONFIRMED)
    
    elif filter_by == 'processing':
        orders =orders.filter(order_status=Order.Status.PROCESSING)    
        
    elif filter_by == 'shipped':
        orders=orders.filter(order_status=Order.Status.SHIPPED)
    
    elif filter_by == 'out_of_delivery':
        orders=orders.filter(order_status=Order.Status.OUT_FOR_DELIVERY)
    
    elif filter_by == 'delivered':
        orders =orders.filter(order_status=Order.Status.DELIVERED)
        
    elif filter_by == 'cancelled':
        orders=orders.filter(order_status=Order.Status.CANCELLED)
    
    payment =request.GET.get('payment')
    if payment :
        orders=orders.filter(payment__payment_method=payment)
    
        
    paginator=Paginator(orders,5)
    page=request.GET.get('page')
    orders=paginator.get_page(page)
    
     
    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(order_status=Order.Status.PENDING).count()
    completed_orders = Order.objects.filter(order_status=Order.Status.DELIVERED).count()
    
    return render(request,'admin/order_list.html',{
        'orders': orders,
        'status': status,
        'search':search,
        'filter_by':filter_by,
        'payment':payment,
        'total_orders':total_orders,
        'pending_orders':pending_orders,
        'completed_orders':completed_orders,
        
    })

@login_required
def  admin_order_detail(request,order_id):
    
    order=get_object_or_404(Order,id=order_id)
    
    items =order.items.select_related('variant__product')
    
    address =getattr(order,'shipping_address',None)
    
    total_items=items.count()
    
    history =order.status_history.all().order_by('-updated_at')
    payment=getattr(order,'payment',None)
    
    can_update =order.order_status not in [
        Order.Status.CANCELLED,
        Order.Status.DELIVERED
    ]

    return render(request, 'admin/order_detail.html', {
        'order':order,
        'items':items,
        'history':history,
        'payment':payment,
        'address':address,
        'total_items':total_items,
        'can_update':can_update,
    })

@login_required
def update_order_status(request,order_id):
    
    if request.method != "POST":
        return redirect('admin_order_detail',order_id=order_id)
    order=get_object_or_404(Order,id =order_id)
    
    new_status=request.POST.get('status')
    
    if order.order_status == Order.Status.CANCELLED :
        messages.error(request,"Cancelled order cannot be updated")
        return redirect('admin_order_detail',order.id)
    #not allow
    if order.order_status == Order.Status.DELIVERED :
        messages.error(request,"Delivered order cannot be updated")
        return redirect('admin_order_detail',order.id)
    
    #pending to confirmed 
    if order.order_status == Order.Status.PENDING:
        if new_status != Order.Status.CONFIRMED:
            messages.error(request,"Only can move to CONFIRMED")
            return redirect('admin_order_detail', order.id)

    # confirmed to proccessing
    elif order.order_status == Order.Status.CONFIRMED:
        if new_status != Order.Status.PROCESSING:
            messages.error(request,"Only can move to PROCESSING")
            return redirect('admin_order_detail', order.id)

    #proccessing to shipped
    elif order.order_status ==Order.Status.PROCESSING:
        if new_status != Order.Status.SHIPPED:
            messages.error(request,"Only can move to SHIPPED")
            return redirect('admin_order_detail',order.id)

    #shipped to out off delvery
    elif order.order_status==Order.Status.SHIPPED:
        if new_status != Order.Status.OUT_FOR_DELIVERY:
            messages.error(request,"Only can move to OUT FOR DELIVERY")
            return redirect('admin_order_detail',order.id)

    # Oout of delvery to delvered
    elif order.order_status ==Order.Status.OUT_FOR_DELIVERY:
        if new_status != Order.Status.DELIVERED:
            messages.error(request,"Only can move to DELIVERED")
            return redirect('admin_order_detail',order.id)
        
    # update status
    order.order_status =new_status
    
     # set delivered date
    if new_status ==Order.Status.DELIVERED:
        order.delivered_date =timezone.now()
    
    order.save()
    
    OrderStatusHistory.objects.create(
        order=order,
        status=new_status
    )
    
    messages.success(request, f"Order moved to {new_status}")
    return redirect('admin_order_detail',order.id)