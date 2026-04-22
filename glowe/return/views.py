from django.shortcuts import render, redirect, get_object_or_404
from .models import ReturnRequest, ReturnImage
from order.models import Order, OrderItem, OrderStatusHistory
from order.refund_utils import process_refund
from decimal import Decimal
from django.contrib import messages
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q


def request_return(request, item_id):
    item = get_object_or_404(OrderItem, id=item_id, order__user=request.user)
    order = item.order

    # Only allow return if order is delivered
    if order.order_status != Order.Status.DELIVERED:
        messages.error(request, "Return not allowed for this order status.")
        return redirect("order_detail", order_id=order.id)

    # Redirect to full order return if discount was applied
    if (order.discount_amount or 0) > 0:
        return redirect("request_full_return", order_id=order.id)


    # return window (7 days)
    if order.delivered_date and timezone.now() > order.delivered_date + timedelta(
        days=7
    ):
        messages.error(request, "Return window has expired (7 days).")
        return redirect("order_detail", order_id=order.id)

    # Check if this item is already requested for return or cancelled
    if item.item_status in [
        OrderItem.Status.CANCELLED,
        OrderItem.Status.RETURN_REQUESTED,
    ]:
        messages.error(
            request,
            "This item has already been cancelled or a return has been requested.",
        )
        return redirect("order_detail", order_id=order.id)

    RETURN_REASONS = [
        "Changed my mind",
        "Ordered by mistake",
        "Received wrong product",
        "Product arrived damaged",
        "Product quality not as expected",
        "Caused skin irritation or allergy",
        "Not suitable for my skin type",
        "Product expired or near expiry",
        "Missing items in package",
        "Packaging was damaged or leaking",
    ]
    ITEM_CONDITIONS = [
        "Unopened (Sealed)",
        "Opened but not used",
        "Used a few times",
        "Damaged on arrival",
        "Leaking or broken packaging",
    ]

    if request.method == "POST":
        reason = request.POST.get("reason")
        description = request.POST.get("description")
        condition = request.POST.get("condition")
        qty_to_return = int(request.POST.get("return_quantity", 1))

        if reason not in RETURN_REASONS:
            messages.error(request, "Please select a valid reason.")
            return redirect("request_return", item_id=item.id)

        if condition not in ITEM_CONDITIONS:
            messages.error(request, "Please select a valid item condition.")
            return redirect("request_return", item_id=item.id)

        # Validation: quantity check
        if qty_to_return < 1 or qty_to_return > item.quantity:
            messages.error(
                request,
                f"Invalid quantity. You can return between 1 and {item.quantity} units.",
            )
            return redirect("request_return", item_id=item.id)

        images = request.FILES.getlist("images")
        if len(images) > 5:
            messages.error(request, "Maximum 5 images allowed.")
            return redirect("request_return", item_id=item.id)

        # create return
        return_request = ReturnRequest.objects.create(
            order_item=item,
            user=request.user,
            quantity=qty_to_return,
            reason=reason,
            description=description,
            item_condition=condition,
        )

        for img in images:
            ReturnImage.objects.create(return_request=return_request, image=img)

        # Update item status
        item.item_status = OrderItem.Status.RETURN_REQUESTED
        item.save()

        messages.success(
            request, "Your return request has been submitted successfully."
        )
        return redirect("order_detail", order_id=order.id)

    # Calculate unit refund ratio (excluding shipping)
    discounted_subtotal = order.subtotal - (order.discount_amount or 0)
    refund_ratio = (discounted_subtotal / order.subtotal) if order.subtotal > 0 else 1
    
    
    item.unit_refund = (item.price_at_time * refund_ratio).quantize(Decimal('0.01'))
  
    item.effective_refund = (item.unit_refund * item.quantity).quantize(Decimal('0.01'))

    return render(
        request,
        "user/return_form.html",
        {
            "item": item,
            "order": order,
            "is_full_order": False,
            "refund_ratio": refund_ratio,
            "RETURN_REASONS": RETURN_REASONS,
            "ITEM_CONDITIONS": ITEM_CONDITIONS,
        },
    )


def request_full_return(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Get all items that not cancelled or already requested for return
    active_items = order.items.filter(
        ~Q(item_status__in=[OrderItem.Status.CANCELLED, OrderItem.Status.RETURN_REQUESTED])
    )

    if not active_items.exists():
        messages.error(request, "No eligible items found for return in this order.")
        return redirect("order_detail", order_id=order.id)

    # only delivered allow
    if order.order_status != Order.Status.DELIVERED:
        messages.error(request, "Return not allowed for this order status.")
        return redirect("order_detail", order_id=order.id)

    # return window (7 days)
    if order.delivered_date and timezone.now() > order.delivered_date + timedelta(days=7):
        messages.error(request, "Return window has expired (7 days).")
        return redirect("order_detail", order_id=order.id)

    RETURN_REASONS = [
        "Changed my mind", "Ordered by mistake", "Received wrong product",
        "Product arrived damaged", "Product quality not as expected",
        "Caused skin irritation or allergy", "Not suitable for my skin type",
        "Product expired or near expiry", "Missing items in package",
        "Packaging was damaged or leaking",
    ]
    ITEM_CONDITIONS = ["Unopened (Sealed)", "Opened but not used", "Used a few times", "Damaged on arrival", "Leaking or broken packaging"]

    if request.method == "POST":
        reason = request.POST.get("reason")
        description = request.POST.get("description")
        condition = request.POST.get("condition")
        
        with transaction.atomic():
            images = request.FILES.getlist("images")
            for item in active_items:
                return_request = ReturnRequest.objects.create(
                    order_item=item,
                    user=request.user,
                    quantity=item.quantity,
                    reason=reason,
                    description=description,
                    item_condition=condition,
                )
                
                # Copy images to each return request (if multiple items, they share the same proof)
                for img in images:
                    ReturnImage.objects.create(return_request=return_request, image=img)
                
                item.item_status = OrderItem.Status.RETURN_REQUESTED
                item.save()

        messages.success(request, "Full order return request submitted successfully.")
        return redirect("order_detail", order_id=order.id)

    # Calculate refund ratio (excluding shipping)
    discounted_subtotal = order.subtotal - (order.discount_amount or 0)
    refund_ratio = (discounted_subtotal / order.subtotal) if order.subtotal > 0 else 1
    for itm in active_items:
        itm.unit_refund = (itm.price_at_time * refund_ratio).quantize(Decimal('0.01'))
        itm.effective_refund = (itm.unit_refund * itm.quantity).quantize(Decimal('0.01'))

    return render(
        request,
        "user/return_form.html",
        {
            "order": order,
            "active_items": active_items,
            "is_full_order": True,
            "refund_ratio": refund_ratio,
            "RETURN_REASONS": RETURN_REASONS,
            "ITEM_CONDITIONS": ITEM_CONDITIONS,
        },
    )


def admin_return_list(request):

    returns = ReturnRequest.objects.select_related(
        "user", "order_item__variant__product", "order_item__order").order_by("-created_at")

    search = request.GET.get("search", "").strip()

    if search:
        returns = returns.filter(
            Q(user__full_name__icontains=search)
            | Q(order_item__variant__product__name__icontains=search))

    status = request.GET.get("status", "")

    if status:
        returns = returns.filter(return_status=status)

    today = timezone.now().date()
    

    pending_count = ReturnRequest.objects.filter(return_status="PENDING").count()
    
    approved_today = ReturnRequest.objects.filter(
        return_status="APPROVED", created_at__date=today).count()
    
    rejected_today = ReturnRequest.objects.filter(
        return_status="REJECTED", created_at__date=today).count()
    
    total_returns = ReturnRequest.objects.count()

    paginator = Paginator(returns, 5)
    page = request.GET.get("page")
    returns = paginator.get_page(page)

    return render(
        request,
        "admin/return_list.html",{
            "returns": returns,
            "search": search,
            "status": status,
            "pending_count": pending_count,
            "approved_today": approved_today,
            "rejected_today": rejected_today,
            "total_returns": total_returns,})


def should_restock(reason, condition):
    
    bad_reasons = [
        "Product arrived damaged",
        "Packaging was damaged or leaking",
        "Caused skin irritation or allergy",
        "Product expired or near expiry",
    ]

    bad_conditions = [
        "Damaged on arrival",
        "Leaking or broken packaging",
        "Used a few times",
    ]
    
    #not add other wise add the stock
    if reason in bad_reasons or condition in bad_conditions:
        
        return False
    
    return True


def admin_return_detail(request, return_id):
    r = get_object_or_404(
        ReturnRequest.objects.select_related(
            "user", "order_item__variant__product", "order_item__order"
        ), 
        id=return_id
    )

    # Calculate estimated refund (excluding shipping)
    item = r.order_item
    order = item.order
    original_item_total = item.price_at_time * r.quantity
    
    if order.subtotal > 0:
        discounted_subtotal = order.subtotal - (order.discount_amount or 0)
        refund_ratio = discounted_subtotal / order.subtotal
        calculated_refund = (original_item_total * refund_ratio).quantize(Decimal('0.01'))
    else:
        calculated_refund = original_item_total

    return render(request, "admin/return_detail.html", {
        "return_request": r,
        "item": item,
        "images": r.images.all(),
        "calculated_refund": calculated_refund,
    })


def approve_return(request, return_id):
    
    r = get_object_or_404(ReturnRequest, id=return_id)
    
    if r.return_status != ReturnRequest.Status.REQUESTED:
        
        messages.error(request, "This return cannot be approved at this stage.")
        return redirect("admin_return_detail", return_id)
    r.return_status = ReturnRequest.Status.APPROVED
    r.save()
    
    messages.success(request, "Return approved.")
    return redirect("admin_return_detail", return_id)


def schedule_pickup(request, return_id):
    
    r = get_object_or_404(ReturnRequest, id=return_id)
    
    if r.return_status != ReturnRequest.Status.APPROVED:
        
        messages.error(request, "Pickup can only be scheduled after approval.")
        return redirect("admin_return_detail", return_id)
    
    r.return_status = ReturnRequest.Status.PICKUP_SCHEDULED
    r.pickup_date = request.POST.get('pickup_date') or (timezone.now() + timedelta(days=1))
    r.save()
    
    messages.success(request, "Pickup scheduled.")
    return redirect("admin_return_detail", return_id)


def mark_picked(request, return_id):
    
    r = get_object_or_404(ReturnRequest, id=return_id)
    
    if r.return_status != ReturnRequest.Status.PICKUP_SCHEDULED:
        
        messages.error(request, "Item can only be picked up after scheduling.")
        return redirect("admin_return_detail", return_id)
    
    with transaction.atomic():
        
        r.return_status = ReturnRequest.Status.PICKED_UP
        r.picked_at = timezone.now()
        r.save()
        
        if should_restock(r.reason, r.item_condition):
            
            variant = r.order_item.variant
            variant.stock += r.quantity
            variant.save()
            
    messages.success(request, "Item picked up and stock updated.")
    return redirect("admin_return_detail", return_id)


def complete_return(request, return_id):
    
    r = get_object_or_404(ReturnRequest, id=return_id)
    
    if r.return_status != ReturnRequest.Status.PICKED_UP:
        messages.error(request, "Return can only be completed after pickup.")
        return redirect("admin_return_detail", return_id)

   
    item = r.order_item
    order = item.order
    
    
    # Calculate refund amount accounting for coupons (excluding shipping)
    original_item_total = item.price_at_time * r.quantity
    
    if order.subtotal > 0:
        discounted_subtotal = order.subtotal - (order.discount_amount or 0)
        refund_ratio = discounted_subtotal / order.subtotal
        refund_amount = (original_item_total * refund_ratio).quantize(Decimal('0.01'))
    else:
        refund_amount = original_item_total

    with transaction.atomic():
       
        process_refund(
            order,
            refund_amount=refund_amount,
            description=(
                f"Refund for returned item '{item.variant.product.name}' "
                f"(x{r.quantity}) in Order #{order.order_number}"
            )
        )

        r.return_status = ReturnRequest.Status.COMPLETED
        r.save()

        # Update item status 
        item.item_status = OrderItem.Status.RETURNED
        item.save()

        # Check if all items in this order are now RETURNED or CANCELLED
        all_items = order.items.all()
        returned_or_cancelled = all_items.filter(item_status__in=[OrderItem.Status.RETURNED, OrderItem.Status.CANCELLED])
        
        if returned_or_cancelled.count() == all_items.count():
            # FULL RETURN
            order.order_status = Order.Status.RETURNED
            msg = "All items in this order have been successfully returned."
        elif returned_or_cancelled.exists():
            # PARTIAL RETURN
            order.order_status = Order.Status.PARTIALLY_RETURNED
            msg = "Some items in this order have been returned."
        
        if order.order_status in [Order.Status.RETURNED, Order.Status.PARTIALLY_RETURNED]:
            order.save()
            # Log this in status history
            from order.models import OrderStatusHistory
            OrderStatusHistory.objects.create(
                order=order,
                status=order.order_status,
                description=msg
            )

    messages.success(request, f"Return completed. ₹{refund_amount} refunded to customer's wallet.")
    return redirect("admin_return_detail", return_id)


def reject_return(request, return_id):
    
    r = get_object_or_404(ReturnRequest, id=return_id)
    
    if r.return_status != ReturnRequest.Status.REQUESTED:
        
        messages.error(request, "Only pending returns can be rejected.")
        return redirect("admin_return_detail", return_id)
    
    r.return_status = ReturnRequest.Status.REJECTED
    r.save()
    
    messages.success(request, "Return rejected.")
    return redirect("admin_return_detail", return_id)
