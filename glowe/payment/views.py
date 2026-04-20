
from django.shortcuts import redirect, get_object_or_404, render
from django.contrib import messages
import razorpay
from order.models import Order, Payment, OrderItem, OrderStatusHistory
from order.email_util import send_order_confirmation_email
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import timedelta


@login_required
def payment_page(request, order_id):

    order = get_object_or_404(Order, id=order_id, user=request.user)
    payment = order.payment

    # already paid
    if payment.payment_status == Payment.Status.SUCCESS:
        return redirect("order_success", order_id=order.id)

    # 5-minute timeout check
    if timezone.now() > order.created_at + timedelta(minutes=5):
        if order.order_status != Order.Status.CANCELLED:
            order.order_status = Order.Status.CANCELLED
            order.save()
            OrderStatusHistory.objects.create(order=order, status=Order.Status.CANCELLED)
            
        messages.error(request, "Payment retry limit exceeded (5 minutes). The order has been cancelled.")
        return redirect("order_detail", order_id=order.id)

    client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )

    # create razorpay order
    razorpay_order = client.order.create({
        "amount": int(order.total_amount * 100),  # paisa
        "currency": "INR",
        "payment_capture": 1,
    })

    # save razorpay order id correctly
    payment.razorpay_order_id = razorpay_order["id"]
    payment.save()

    expiration_time = order.created_at + timedelta(minutes=5)
    time_left_seconds = max(0, int((expiration_time - timezone.now()).total_seconds()))

    context = {
        "order": order,
        "payment": payment,
        "razorpay_key": settings.RAZORPAY_KEY_ID,
        "razorpay_order_id": razorpay_order["id"],
        "amount": int(order.total_amount * 100),
        "time_left_seconds": time_left_seconds,
    }

    return render(request, "payment/payment_page.html", context)


@csrf_exempt
def verify_payment(request):
    # Try to get data from both POST and GET
    data = request.POST if request.method == "POST" else request.GET

    order_id = request.GET.get("order_id") or data.get("order_id")
    razorpay_order_id = data.get("razorpay_order_id")
    razorpay_payment_id = data.get("razorpay_payment_id")
    razorpay_signature = data.get("razorpay_signature")

    if not order_id:
        messages.error(request, "Invalid payment request.")
        return redirect("home")

    # Find the order
    order = get_object_or_404(Order, id=order_id)
    payment = order.payment

    client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )

    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature
        })

        with transaction.atomic():
            payment.payment_status = Payment.Status.SUCCESS
            payment.razorpay_payment_id = razorpay_payment_id
            payment.razorpay_signature = razorpay_signature
            payment.transaction_id = razorpay_payment_id
            payment.save()

            order.order_status = Order.Status.CONFIRMED
            order.save()

            # Reduce stock here
            for item in order.items.all():
                variant = item.variant
                variant.stock -= item.quantity
                variant.save()

            # Log history
            OrderStatusHistory.objects.create(
                order=order,
                status=Order.Status.CONFIRMED
            )
            
            # Send confirmation email
            try:
                send_order_confirmation_email(request, order)
            except Exception as e:
                print("Email failed:", e)

        messages.success(request, "Payment successful. Order confirmed")
        return redirect("order_success", order_id=order.id)

    except Exception as e:
        print("ERROR:", e)
        payment.payment_status = Payment.Status.FAILED
        payment.save()
        messages.error(request, "Payment failed. Try again")
        return redirect("payment_failed", order_id=order.id)

@login_required
def payment_failed(request, order_id):

    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Mark as failed if user abandons/closes the payment
    try:
        payment = order.payment
        if payment.payment_status == Payment.Status.PENDING:
            payment.payment_status = Payment.Status.FAILED
            payment.save()
    except Exception:
        pass

    expiration_time = order.created_at + timedelta(minutes=5)
    time_left_seconds = max(0, int((expiration_time - timezone.now()).total_seconds()))
    retry_allowed = time_left_seconds > 0
    
    if not retry_allowed and order.order_status != Order.Status.CANCELLED:
        order.order_status = Order.Status.CANCELLED
        order.save()
        OrderStatusHistory.objects.create(order=order, status=Order.Status.CANCELLED)

    return render(request, "payment/payment_failed.html", {
        "order": order,
        "retry_allowed": retry_allowed,
        "time_left_seconds": time_left_seconds,
    })
