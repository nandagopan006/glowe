
from django.shortcuts import redirect, get_object_or_404, render
from django.contrib import messages
import razorpay
from order.models import Order,Payment,OrderItem,OrderStatusHistory
from django.contrib.auth.decorators import login_required
from django.conf import settings


import razorpay
from django.conf import settings                 

@login_required
def payment_page(request, order_id):

    order = get_object_or_404(Order, id=order_id, user=request.user)
    payment = order.payment

    # already paid
    if payment.payment_status == Payment.Status.SUCCESS:
        return redirect("order_success", order_id=order.id)

    client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )

    # create razorpay order
    razorpay_order = client.order.create({
        "amount": int(order.total_amount * 100),  # paisa
        "currency": "INR",
        "payment_capture": 1,
    })

    # save order id
    payment.transaction_id = razorpay_order["id"]
    payment.save()

    context = {
        "order": order,
        "payment": payment,
        "razorpay_key": settings.RAZORPAY_KEY_ID,
        "razorpay_order_id": razorpay_order["id"],
        "amount": int(order.total_amount * 100),
    }

    return render(request, "user/payment_page.html", context)


@login_required
def verify_payment(request):

    order_id = request.GET.get("order_id")
    razorpay_order_id = request.GET.get("razorpay_order_id")
    razorpay_payment_id = request.GET.get("razorpay_payment_id")
    razorpay_signature = request.GET.get("razorpay_signature")

    order = get_object_or_404(Order, id=order_id, user=request.user)
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

        # success 
        payment.payment_status = Payment.Status.SUCCESS
        payment.transaction_id = razorpay_payment_id
        payment.save()

        order.order_status = Order.Status.CONFIRMED
        order.save()

        # reduce stock here
        for item in order.items.all():
            variant = item.variant
            variant.stock -= item.quantity
            variant.save()

        OrderStatusHistory.objects.create(
            order=order,
            status=Order.Status.CONFIRMED
        )

        messages.success(request, "Payment successful")
        return redirect("order_success", order_id=order.id)

    except:
        # failed
        payment.payment_status = Payment.Status.FAILED
        payment.save()

        messages.error(request, "Payment verification failed")
        return redirect("payment_failed", order_id=order.id)


@login_required
def payment_failed(request, order_id):

    order = get_object_or_404(Order, id=order_id, user=request.user)

    return render(request, "user/payment_failed.html", {
        "order":order
    })
