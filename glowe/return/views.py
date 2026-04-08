from django.shortcuts import render, redirect, get_object_or_404
from .models import ReturnRequest, ReturnImage
from order.models import Order, OrderItem, OrderStatusHistory
from django.contrib import messages
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.decorators import login_required


def request_return(request, item_id):
    item = get_object_or_404(OrderItem, id=item_id, order__user=request.user)
    order = item.order

    # only delivered allow
    if order.order_status != Order.Status.DELIVERED:
        messages.error(request, "Return not allowed for this order status.")
        return redirect("order_detail", order_id=order.id)

    # return window (7 days)
    if order.delivered_date and timezone.now() > order.delivered_date + timedelta(days=7):
        messages.error(request, "Return window has expired (7 days).")
        return redirect("order_detail", order_id=order.id)

    # Check if this item is already requested for return or cancelled
    if item.item_status in [OrderItem.Status.CANCELLED, OrderItem.Status.RETURN_REQUESTED]:
        messages.error(request, "This item has already been cancelled or a return has been requested.")
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
            messages.error(request, f"Invalid quantity. You can return between 1 and {item.quantity} units.")
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

        messages.success(request, "Your return request has been submitted successfully.")
        return redirect("order_detail", order_id=order.id)

    return render(
        request,
        "user/return_form.html",
        {
            "item": item,
            "order": order,
            "RETURN_REASONS": RETURN_REASONS,
            "ITEM_CONDITIONS": ITEM_CONDITIONS,
        },
    )
