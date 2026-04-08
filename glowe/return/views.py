from django.shortcuts import render, redirect, get_object_or_404
from .models import ReturnRequest, ReturnImage
from order.models import Order, OrderItem, OrderStatusHistory
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

    # only delivered allow
    if order.order_status != Order.Status.DELIVERED:
        messages.error(request, "Return not allowed for this order status.")
        return redirect("order_detail", order_id=order.id)

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


def admin_return_list(request):

    returns = ReturnRequest.objects.select_related(
        "user", "order_item__variant__product", "order_item__order"
    ).order_by("-created_at")

    search = request.GET.get("search", "").strip()

    if search:
        returns = returns.filter(
            Q(user__full_name__icontains=search)
            | Q(order_item__variant__product__name__icontains=search)
        )

    status = request.GET.get("status", "")

    if status:
        returns = returns.filter(return_status=status)

    today = timezone.now().date()
    all_returns = ReturnRequest.objects.all()

    pending_count = ReturnRequest.objects.filter(return_status="PENDING").count()
    approved_today = ReturnRequest.objects.filter(
        return_status="APPROVED", updated_at__date=today
    ).count()
    rejected_today = ReturnRequest.objects.filter(
        return_status="REJECTED", updated_at__date=today
    ).count()
    total_returns = ReturnRequest.objects.count()

    paginator = Paginator(returns, 5)
    page = request.GET.get("page")
    returns = paginator.get_page(page)

    return render(
        request,
        "admin/return_list.html",
        {
            "returns": returns,
            "search": search,
            "status": status,
            "pending_count": pending_count,
            "approved_today": approved_today,
            "rejected_today": rejected_today,
            "total_returns": total_returns,
        },
    )


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
    if reason in bad_reasons or condition in bad_conditions:
        return False
    return True


def admin_return_detail(request, return_id):
    r = get_object_or_404(
        ReturnRequest.objects.select_related(
            "user", "order_item__variant__product", "order_item__order"
        ),
        id=return_id,
    )
    return render(request, "admin/return_detail.html", {
        "return_request": r,
        "item": r.order_item,
        "images": r.images.all(),
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
    r.pickup_date = timezone.now() + timedelta(days=1)
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
    r.return_status = ReturnRequest.Status.COMPLETED
    r.save()
    messages.success(request, "Return completed.")
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
