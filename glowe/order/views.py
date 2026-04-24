from accounts import models
from django.shortcuts import redirect, get_object_or_404, render
from order.refund_utils import process_refund
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
from django.apps import apps
from order.email_util import send_order_confirmation_email, send_order_cancellation_email, send_order_delivered_email
from coupons.views import calculate_discount
from coupons.models import Coupon, CouponUsage
from decimal import Decimal
from wallet.models import WalletTransaction
from offer.utils import get_best_offer

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
    payment_method = request.POST.get("payment_method")
    
    if not address_id:
        request.session["order_processing"] = False
        messages.error(request, "Please select a delivery address")
        return redirect("checkout")

    address = get_object_or_404(Address, id=address_id, user=request.user)

    subtotal = Decimal('0.00')

    with transaction.atomic():
        for item in cart_items:
            # lock variant ,,if one user bbuy same other USER aslo nedd lock  --oveerselling block
            variant =Variant.objects.select_for_update().get(id=item.variant.id)
            product=variant.product

            if not product.is_active or product.is_deleted:
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

            
            price = Decimal("0.00")
            try:
                price = Decimal(str(variant.price))
                offer, offer_disc = get_best_offer(product, price)
                
                if offer:
                    if offer_disc > price:
                        offer_disc = price  # Discount cannot exceed price
                        
                    final_price = price - offer_disc
                    
                    if final_price < Decimal("0.00"):
                        final_price = Decimal("0.00")  # No negative price
                else:
                    final_price = price
                    
            except Exception:
                # If error, use the regular price
                final_price = price
            
            item.item_total = item.quantity * final_price
            item.offer_price = final_price  # Store final price for the order item
            subtotal += Decimal(item.item_total)

        shipping = Decimal('0.00') if subtotal > Decimal('999') else Decimal('100.00')
        
        # Calculate discount
        discount = calculate_discount(request, subtotal)
        total = subtotal + shipping - discount
        if total < 0: total = Decimal('0.00')

        order = Order.objects.create(
            user=request.user,
            order_number="ORD-" + get_random_string(10).upper(),
            address=address,
            subtotal=subtotal,
            delivery_charge=shipping,
            discount_amount=discount,
            total_amount=total,
            order_status=Order.Status.PENDING,
        )

        # create order items + reduce stock
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                variant=item.variant,
                price_at_time=item.offer_price,
                quantity=item.quantity,
            )

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

        Payment.objects.create(
            order=order, 
            amount=total, 
            payment_method=payment_method, 
            payment_status=Payment.Status.PENDING
        )
        
        # Store coupon ID specifically for THIS order to prevent multi-tab issues
        coupon_id = request.session.get('coupon_id')
        if coupon_id and discount > 0:
            request.session[f'order_coupon_{order.id}'] = coupon_id

        
        # Initial status history
        OrderStatusHistory.objects.create(order=order, status=Order.Status.PENDING)
        
        # If COD, confirm immediately and reduce stock
        if payment_method == Payment.Method.COD:
            order.order_status = Order.Status.CONFIRMED
            order.save()
            
            OrderStatusHistory.objects.create(order=order, status=Order.Status.CONFIRMED)
            
            for item in order.items.all():
                v = item.variant
                v.stock -= item.quantity
                v.save()
            
            try:
                send_order_confirmation_email(request, order)
            except:
                pass

        cart_items.delete()

    # for geting the current
    request.session["last_order_id"] = order.id

    request.session["order_processing"] = False
    
    # redirect bases on pyment 
    if payment_method == Payment.Method.COD:
        return redirect("order_success",order_id=order.id)
    elif payment_method == Payment.Method.WALLET:
        return redirect("process_wallet_payment", order_id=order.id)
    else:
        return redirect("payment_page",order_id=order.id)

    


@login_required
def order_success(request, order_id):
    # get order the user
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # only confirmed order can see success page
    if order.order_status != Order.Status.CONFIRMED:
        messages.warning(request, "Your order is currently pending confirmation.")
        return redirect("order_listing")

    # onlyy the now done order
    last_order_id = request.session.get("last_order_id")
    if last_order_id != order.id:
        return redirect("home")

   
    # if coupon used increment count
    # Check for order-specific coupon first, then fallback to current session
    coupon_id = request.session.get(f'order_coupon_{order.id}') or request.session.get('coupon_id')
    
    if coupon_id and order.discount_amount > 0:
        try:
            with transaction.atomic():
                coupon = Coupon.objects.select_for_update().get(id=coupon_id)
                coupon.used_count += 1
                coupon.save()
                
                usage, created = CouponUsage.objects.get_or_create(user=request.user, coupon=coupon)
                usage.used_count += 1
                usage.save()
                
                # Remove both specific and general session keys
                if f'order_coupon_{order.id}' in request.session:
                    del request.session[f'order_coupon_{order.id}']
                
                # Only clear general if it matches the one used
                if request.session.get('coupon_id') == coupon_id:
                    del request.session['coupon_id']
                    if 'coupon_code' in request.session:
                        del request.session['coupon_code']

        except Coupon.DoesNotExist:
            pass


    # get all items this order
    order_items = order.items.select_related("variant", "variant__product")

    # direct access not not alllow  like not place order
    if not order_items.exists():
        return redirect("home")

    order_date = order.created_at.date()
    delivery_start = order_date + timedelta(days=3)
    delivery_end = order_date + timedelta(days=7)

    # get payment
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

    ReturnRequest = apps.get_model('return', 'ReturnRequest')
    for order in orders:
        order.delivery_start = order.created_at + timedelta(days=3)
        order.delivery_end = order.created_at + timedelta(days=7)

        # cancelled items  the item count or create duplicate images
        active = [item for item in order.items.all() if item.item_status != "CANCELLED"]
        order.display_items = active if active else list(order.items.all())
        
        order.return_badge = None
        returns = ReturnRequest.objects.filter(order_item__order=order)
        
        has_active = False
        has_completed = False
        
        for r in returns:
            if r.return_status == 'COMPLETED':
                has_completed = True
            elif r.return_status != 'REJECTED':
                has_active = True
                
        if has_active:
            order.return_badge = "Return Active"
        elif has_completed:
            order.return_badge = "Returned"
            
    total_orders = orders.count()
    paginator = Paginator(orders, 5)
    page = request.GET.get("page")
    orders = paginator.get_page(page)

    return render(
        request,"user/order_listing.html",{
            "orders":orders,
            "search":search,
            "filter_by":filter_by,
            "total_orders":total_orders,})


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # not cancelled item
    active_items = (
        order.items.exclude(item_status=OrderItem.Status.CANCELLED)
        .select_related("variant__product")
        .prefetch_related("variant__product__images")
    )

    cancelled_items = (
        order.items.filter(item_status=OrderItem.Status.CANCELLED)
        .select_related("variant__product")
        .prefetch_related("variant__product__images")
    )

    for item in active_items:
        item.subtotal = item.price_at_time * item.quantity

    for item in cancelled_items:
        item.subtotal = item.price_at_time * item.quantity

    grouped = {}
    for item in cancelled_items:
        variant_id = item.variant_id

        if variant_id not in grouped:

            grouped[variant_id] = {
                "variant": item.variant,
                "price_at_time": item.price_at_time,
                "quantity": item.quantity,
                "subtotal": item.subtotal,
                "cancel_reason": item.cancel_reason,
            }
        else:
            # Same variant + new
            grouped[variant_id]["quantity"] += item.quantity

    cancelled_items = list(grouped.values())

    # Chck if all items are cancelled
    all_cancelled = not active_items.exists()

    order.delivery_start = order.created_at + timedelta(days=3)
    order.delivery_end = order.created_at + timedelta(days=7)

    history = order.status_history.all().order_by("-updated_at")

    can_cancel = order.order_status in [
        Order.Status.CONFIRMED,
        Order.Status.PROCESSING,
    ]
    can_return = order.order_status == Order.Status.DELIVERED
    payment = getattr(order, "payment", None)

    expiration_time = order.created_at + timedelta(minutes=5)
    time_left_seconds = max(0, int((expiration_time - timezone.now()).total_seconds()))
    
    # Auto-cancel if pending and time exceeded
    if order.order_status == Order.Status.PENDING and time_left_seconds <= 0:
        order.order_status = Order.Status.CANCELLED
        order.save()
        OrderStatusHistory.objects.create(order=order, status=Order.Status.CANCELLED)
        if payment and payment.payment_status == Payment.Status.PENDING:
            payment.payment_status = Payment.Status.FAILED
            payment.save()
            
    retry_allowed = (order.order_status == Order.Status.PENDING and time_left_seconds > 0)

    # cancelled_items
    if all_cancelled:
        total_count = len(cancelled_items)
    else:
        total_count = active_items.count()

    ReturnRequest = apps.get_model('return', 'ReturnRequest')
    returns = ReturnRequest.objects.filter(order_item__order=order).prefetch_related('images', 'order_item__variant__product__images').order_by('-created_at')

    # Check for refund
    
    wallet_refund = WalletTransaction.objects.filter(
        order=order, 
        transaction_type='REFUND',
        status='COMPLETED'
    ).first()

    # Check if a full return or any return is already in progress
    full_return_requested = returns.exists()

    return render(
        request,
        "user/order_detail.html",
        {
            "order":order,
            "active_items":active_items,
            "cancelled_items":cancelled_items,
            "all_cancelled":all_cancelled,
            "history":history,
            "delivery_start":order.delivery_start,
            "delivery_end":order.delivery_end,
            "can_cancel":can_cancel,
            "can_return":can_return and not full_return_requested,
            "payment":payment,
            "total_count":total_count,
            "returns":returns,
            "returned_item_ids": [r.order_item.id for r in returns],
            "retry_allowed": retry_allowed,
            "time_left_seconds": time_left_seconds,
            "wallet_refund": wallet_refund,
            "full_return_requested": full_return_requested,
        },
    )


@login_required
def cancel_order(request, order_id):

    if request.method != "POST":
        return redirect("order_detail", order_id=order_id)

    order = get_object_or_404(Order, id=order_id, user=request.user)

    # chck allowed only
    if order.order_status not in [
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

        order.order_status = Order.Status.CANCELLED
        order.save()
        
        payment = getattr(order, 'payment', None)
        if payment and payment.payment_method == Payment.Method.COD:
            payment.payment_status = Payment.Status.FAILED
            payment.save()

    # Process refund to wallet (skips COD orders that were never delivered)
    refunded = process_refund(
        order,
        refund_amount=order.total_amount,
        description=f"Refund for cancelled Order #{order.order_number}"
    )
    refund_amount = order.total_amount if refunded else None

    # Status history
    OrderStatusHistory.objects.create(order=order, status=Order.Status.CANCELLED)
    # Cancellation email
    send_order_cancellation_email(request, order, is_full_cancel=True, refund_amount=refund_amount)

    messages.success(request, "Order cancelled successfully")
    return redirect("order_cancelled_success", order_id=order.id)


@login_required
def cancel_order_item(request, item_id):

    if request.method != "POST":
        return redirect("home")

    item = get_object_or_404(OrderItem, id=item_id, order__user=request.user)

    order = item.order

    if order.order_status not in [
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
        quantity_to_cancel =int(request.POST.get("quantity", item.quantity))
        
    except (ValueError,TypeError):
        quantity_to_cancel =item.quantity

    if quantity_to_cancel > item.quantity or quantity_to_cancel <= 0:
        messages.error(request, "Invalid quantity")
        return redirect("order_detail", order_id=order.id)

    with transaction.atomic():
        # Restore stock for cancelled portion
        variant = item.variant
        variant.stock += quantity_to_cancel
        variant.save()

        # Update order subtotal
        cancelled_amount = item.price_at_time * quantity_to_cancel
        order.subtotal -= cancelled_amount

        # partial cancel
        if quantity_to_cancel < item.quantity:
            # Reduce original item quantity
            item.quantity -= quantity_to_cancel
            item.save()

            # Createnew record for cancelled
            cancelled_item = OrderItem.objects.create(
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
            cancelled_item = item

        # total
        order.total_amount = order.subtotal + order.delivery_charge
        order.save()

        # history
        OrderStatusHistory.objects.create(order=order, status="ITEM_CANCELLED")

        # Check if all items in the order are now cancelled
        all_cancelled = not order.items.filter(
            ~Q(item_status=OrderItem.Status.CANCELLED)
        ).exists()
        if all_cancelled:
            order.order_status = Order.Status.CANCELLED
            order.save()

    # skips COD if not delivered
    refunded = process_refund(
        order,
        refund_amount=cancelled_amount,
        description=f"Refund for cancelled item in Order #{order.order_number} — {item.variant.product.name}"
    )
    email_refund_amount = cancelled_amount if refunded else None

    # Cancellation email
    send_order_cancellation_email(
        request, 
        order, 
        cancelled_items=[cancelled_item], 
        is_full_cancel=False, 
        refund_amount=email_refund_amount
    )

    messages.success(request, "Item cancelled succussfully")
    return redirect("order_cancelled_success", order_id=order.id)


@login_required
def order_cancelled_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Get all cancelled items for this order
    cancelled_items = order.items.filter(
        item_status=OrderItem.Status.CANCELLED
    ).select_related("variant__product")

    if not cancelled_items.exists():
        return redirect("order_detail", order_id=order_id)

    #if the entire order is cancelled
    total_items = order.items.count()
    full_cancelled = cancelled_items.count() == total_items

    cancellation_id = f"CNCL-{str(order.id).zfill(5)}"

    # Get payment method info
    payment = getattr(order, "payment", None)

    # Check if a wallet refund was issued for this cancellation
    from wallet.models import WalletTransaction
    wallet_refund = WalletTransaction.objects.filter(
        order=order,
        transaction_type='REFUND',
        status='COMPLETED',
    ).first()

    return render(
        request,
        "user/order_cancelled.html",
        {
            "order": order,
            "cancelled_items": cancelled_items,
            "cancellation_id": cancellation_id,
            "payment": payment,
            "wallet_refund": wallet_refund,
        },
    )


@login_required
def download_invoice(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # FILTER ACTIVE ITEMS ONLY
    active_items = order.items.exclude(item_status=OrderItem.Status.CANCELLED)
    
    if not active_items.exists():
        messages.error(request, "Cannot download invoice for a fully cancelled order.")
        return redirect('order_detail', order_id=order.id)

    addr = order.shipping_address
    pay = getattr(order, "payment", None)

    styles = getSampleStyleSheet()
    B = lambda t: Paragraph(f"<b>{t}</b>", styles["Normal"])
    N = lambda t: Paragraph(str(t), styles["Normal"])
    INR = lambda v: f"Rs.{v:,.2f}"

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=30, bottomMargin=30)

    meta = Table(
        [[B("Glowe"), B(f"INVOICE # {order.order_number}")]], colWidths=[270, 270]
    )
    meta.setStyle(TableStyle([("ALIGN", (1, 0), (1, 0), "RIGHT")]))

    info = Table(
        [
            [B("Bill To"), B("Ship To"), B("Payment")],
            [
                N(order.user.get_full_name()),
                N(addr.full_name),
                N(pay.get_payment_method_display() if pay else "—"),
            ],
            [
                N(order.user.email),
                N(addr.address_line1),
                N(pay.get_payment_status_display() if pay else "—"),
            ],
            ["", N(f"{addr.city}, {addr.state} {addr.pincode}"), ""],
            ["", N(addr.country), ""],
        ],
        colWidths=[180, 180, 180],
    )
    info.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.black),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )

    # Group items by variant (excluding cancelled)
    grouped = defaultdict(lambda: {"name": "", "qty": 0, "price": 0})
    for item in active_items:
        key = item.variant.id
        grouped[key]["name"] = item.variant.product.name[:50]
        grouped[key]["price"] = item.price_at_time
        grouped[key]["qty"] += item.quantity

    # Build item rows
    rows = [["Product", "Qty", "Unit Price", "Amount"]]
    for g in grouped.values():
        qty = g["qty"]
        price = g["price"]
        rows.append([g["name"], qty, INR(price), INR(qty * price)])

    # Compute totals dynamically from active items
    computed_subtotal = sum(g["qty"] * g["price"] for g in grouped.values())
    discount = order.discount_amount
    shipping = order.delivery_charge
    computed_total = max(0, computed_subtotal + shipping - discount)

    rows += [
        ["", "", "Subtotal", INR(computed_subtotal)],
        ["", "", "Shipping", INR(shipping)],
    ]
    
    if discount > 0:
        rows.append(["", "", "Discount", f"-{INR(discount)}"])
        
    rows.append(["", "", B("Total Amount"), B(INR(computed_total))])

    table = Table(rows, colWidths=[300, 60, 80, 100])
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BACKGROUND", (0, 0), (-1, 0), colors.black),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
                ("LINEABOVE", (0, -3) if discount == 0 else (0, -4), (-1, -3) if discount == 0 else (-1, -4), 0.5, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )

    doc.build([meta, Spacer(1, 8), info, Spacer(1, 16), table])
    buf.seek(0)
    res = HttpResponse(buf, content_type="application/pdf")
    res["Content-Disposition"] = (
        f'attachment; filename="invoice_{order.order_number}.pdf"'
    )
    return res


# -------- end user side ---- -- -- - - - - - ok


# --start ---admin side---- - - - - - -------


def admin_order_list(request):

    orders = Order.objects.select_related("user").all()
    orders = orders.order_by("-created_at")

    search = request.GET.get("search", "").strip()

    if search:
        orders = orders.filter(
            Q(order_number__icontains=search) | Q(user__full_name__icontains=search)
        )

    status = request.GET.get("status", "")
    if status:
        orders = orders.filter(order_status=status)

    filter_by = request.GET.get("filter", "all")

    if filter_by == "pending":
        orders = orders.filter(order_status=Order.Status.PENDING)

    elif filter_by == "confirmed":
        orders = orders.filter(order_status=Order.Status.CONFIRMED)

    elif filter_by == "processing":
        orders = orders.filter(order_status=Order.Status.PROCESSING)

    elif filter_by == "shipped":
        orders = orders.filter(order_status=Order.Status.SHIPPED)

    elif filter_by == "out_of_delivery":
        orders = orders.filter(order_status=Order.Status.OUT_FOR_DELIVERY)

    elif filter_by == "delivered":
        orders = orders.filter(order_status=Order.Status.DELIVERED)

    elif filter_by == "cancelled":
        orders = orders.filter(order_status=Order.Status.CANCELLED)

    payment = request.GET.get("payment")
    if payment:
        orders = orders.filter(payment__payment_method=payment)

    paginator = Paginator(orders, 5)
    page = request.GET.get("page")
    orders = paginator.get_page(page)

    # Group items  if exist need increase
    for order in orders:
        items_grouped = {}
        for item in order.items.all().select_related("variant__product"):
            v_id = item.variant.id
            if v_id not in items_grouped:
                items_grouped[v_id] = {
                    "product_id": item.variant.product.id,
                    "name": item.variant.product.name,
                    "image": (
                        item.variant.product.images.first().image.url
                        if item.variant.product.images.first()
                        else None
                    ),
                    "quantity": item.quantity,
                    "price": item.price_at_time,
                }
            else:
                items_grouped[v_id]["quantity"] += item.quantity

        order.display_items = list(items_grouped.values())

    total_orders=Order.objects.count()
    pending_orders=Order.objects.filter(order_status=Order.Status.PENDING).count()
    completed_orders=Order.objects.filter(order_status=Order.Status.DELIVERED).count()

    return render(
        request,
        "admin/order_list.html",{
            "orders":orders,
            "status":status,
            "search":search,
            "filter_by":filter_by,
            "payment":payment,
            "total_orders":total_orders,
            "pending_orders":pending_orders,
            "completed_orders":completed_orders,
        })


def admin_order_detail(request, order_id):

    order = get_object_or_404(Order.objects.prefetch_related(
        "items__variant__product", 
        "items__returnrequest_set"
    ), id=order_id)

    items = order.items.all()
    
    # Calculate subtotal for each item in the view to avoid model changes
    for item in items:
        item.subtotal = item.price_at_time * item.quantity

    address = getattr(order, "shipping_address", None)

    total_items = items.count()

    history = order.status_history.all().order_by("-updated_at")
    payment = getattr(order, "payment", None)

    can_update = order.order_status not in [
        Order.Status.CANCELLED,
        Order.Status.DELIVERED,
    ]

    # Check for returns associated with this order
    ReturnRequest = apps.get_model('return', 'ReturnRequest')
    all_returns = ReturnRequest.objects.filter(order_item__order=order).select_related('order_item__variant__product')

    has_any_return = False
    is_fully_returned = True

    for item in items:
        # If this item was returned, mark it correctly
        if all_returns.filter(order_item=item, return_status='COMPLETED').exists():
            if item.item_status != OrderItem.Status.RETURNED:
                item.item_status = OrderItem.Status.RETURNED
                item.save()
        
        # Track for overall order status
        if item.item_status == OrderItem.Status.RETURNED:
            has_any_return = True
        elif item.item_status != OrderItem.Status.CANCELLED:
            is_fully_returned = False

    # Update order status if needed
    if has_any_return:
        target_status = Order.Status.RETURNED if is_fully_returned else Order.Status.PARTIALLY_RETURNED
        if order.order_status != target_status:
            order.order_status = target_status
            order.save()
            
            # Simple log for the history
            from order.models import OrderStatusHistory
            if not OrderStatusHistory.objects.filter(order=order, status=target_status).exists():
                OrderStatusHistory.objects.create(
                    order=order, 
                    status=target_status, 
                    description=f"Status updated to {target_status} after return check."
                )

    # Check for refund
    from wallet.models import WalletTransaction
    wallet_refund = WalletTransaction.objects.filter(
        order=order, 
        transaction_type='REFUND',
        status='COMPLETED'
    ).first()

    return render(
        request,
        "admin/order_detail.html",
        {
            "order": order,
            "items": items,
            "history": history,
            "payment": payment,
            "address": address,
            "total_items": total_items,
            "can_update": can_update,
            "wallet_refund": wallet_refund,
            "all_returns": all_returns,
        },
    )


def update_order_status(request, order_id):

    if request.method != "POST":
        return redirect("admin_order_detail", order_id=order_id)
    order = get_object_or_404(Order, id=order_id)

    new_status = request.POST.get("status")

    if order.order_status == Order.Status.CANCELLED:
        messages.error(request, "Cancelled order cannot be updated")
        return redirect("admin_order_detail", order.id)
    # not allow
    if order.order_status == Order.Status.DELIVERED:
        messages.error(request, "Delivered order cannot be updated")
        return redirect("admin_order_detail", order.id)

    # same status
    if new_status == order.order_status:
        messages.error(request, "Order already in this status")
        return redirect("admin_order_detail", order.id)

    # pending to confirmed
    if order.order_status == Order.Status.PENDING:
        if new_status != Order.Status.CONFIRMED:
            messages.error(request, "Only can move to CONFIRMED")
            return redirect("admin_order_detail", order.id)

    # confirmed to proccessing
    elif order.order_status == Order.Status.CONFIRMED:
        if new_status != Order.Status.PROCESSING:
            messages.error(request, "Only can move to PROCESSING")
            return redirect("admin_order_detail", order.id)

    # proccessing to shipped
    elif order.order_status == Order.Status.PROCESSING:
        if new_status != Order.Status.SHIPPED:
            messages.error(request, "Only can move to SHIPPED")
            return redirect("admin_order_detail", order.id)

    # shipped to out off delvery
    elif order.order_status == Order.Status.SHIPPED:
        if new_status != Order.Status.OUT_FOR_DELIVERY:
            messages.error(request, "Only can move to OUT FOR DELIVERY")
            return redirect("admin_order_detail", order.id)

    # Oout of delvery to delvered
    elif order.order_status == Order.Status.OUT_FOR_DELIVERY:
        if new_status != Order.Status.DELIVERED:
            messages.error(request, "Only can move to DELIVERED")
            return redirect("admin_order_detail", order.id)

    # update status
    with transaction.atomic():

        order.order_status = new_status

        if new_status == Order.Status.DELIVERED:
            order.delivered_date = timezone.now()
            
            # Sync item statuses to DELIVERED
            order.items.filter(
                ~Q(item_status=OrderItem.Status.CANCELLED)
            ).update(item_status=OrderItem.Status.DELIVERED)

            #cod pyment update
            payment = getattr(order, "payment", None)
            if payment and payment.payment_method == Payment.Method.COD:
                payment.payment_status = Payment.Status.SUCCESS
                payment.save()
            
            # Send premium Everlane-style delivery email
            send_order_delivered_email(request, order)

        order.save()

        OrderStatusHistory.objects.create(order=order, status=new_status)

    messages.success(request, f"Order status updated to {new_status}")
    return redirect("admin_order_detail",order.id)
