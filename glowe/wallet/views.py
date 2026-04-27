from django.shortcuts import render
from django.core.paginator import Paginator
from .models import Wallet
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Wallet, WalletTransaction
from payment.utils import create_razorpay_order
from decimal import Decimal, InvalidOperation
from payment.utils import verify_payment_signature
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.cache import never_cache
from django.contrib import messages
from order.models import Order, Payment, OrderStatusHistory
from order.email_util import send_order_confirmation_email
from product.models import Variant


@never_cache
@login_required
def wallet_view(request):
    wallet,created = Wallet.objects.get_or_create(user=request.user)

    #Mark pending add trantns older than 1 mtns as fail
    check_time = timezone.now() - timedelta(minutes=1)
    WalletTransaction.objects.filter(
        wallet=wallet, 
        status='PENDING', 
        transaction_type='ADD',
        created_at__lt=check_time
    ).update(status='FAILED')

    transactions_list = wallet.transactions.all().order_by('-created_at')

    paginator=Paginator(transactions_list,7)
    page_number=request.GET.get('page')
    transactions =paginator.get_page(page_number)

    return render(request,'wallet.html',{
        'wallet':wallet,
        'transactions':transactions
    })
    

@login_required
def create_wallet_order(request):
    try:
        amount = request.POST.get("amount")

        #Validate amount
        try:
            amount = Decimal(amount)
        except (InvalidOperation, TypeError):
            return JsonResponse({"error": "Invalid amount format"}, status=400)

        if amount <= 0:
            return JsonResponse({"error": "Amount must be greater than 0"}, status=400)

    
        if amount > 50000:
            return JsonResponse({"error": "Maximum ₹50,000 allowed"}, status=400)

        #Get wallet
        wallet, _ = Wallet.objects.get_or_create(user=request.user)

        # Create Razorpay order
        razorpay_order = create_razorpay_order(amount)

        txn = WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type="ADD",
            amount=amount,
            status="PENDING",
            description="Wallet top-up",
            transaction_id=razorpay_order["id"]  
        )

        return JsonResponse({
            "order_id": razorpay_order["id"],
            "amount": int(amount * 100),
            "key": settings.RAZORPAY_KEY_ID,
            "txn_id": txn.id
        })

    except Exception as e:
        print("Wallet Order Error:", e)
        return JsonResponse({"error": "Something went wrong"}, status=500)
    
    

@csrf_exempt
@login_required
def verify_wallet_payment(request):

    txn_id = request.POST.get("txn_id")
    razorpay_order_id = request.POST.get("razorpay_order_id")
    razorpay_payment_id = request.POST.get("razorpay_payment_id")
    razorpay_signature = request.POST.get("razorpay_signature")

    # Validate input
    if not txn_id:
        return JsonResponse({"status": "invalid_request"}, status=400)

    try:
        txn = WalletTransaction.objects.select_related("wallet").get(id=txn_id)
    except WalletTransaction.DoesNotExist:
        return JsonResponse({"status": "invalid_transaction"}, status=404)

    # ensure user owns this wallet
    if txn.wallet.user != request.user:
        return JsonResponse({"status": "unauthorized"}, status=403)

    #Prevent double credit
    if txn.status == "COMPLETED":
        return JsonResponse({"status": "already_processed"})

    #Verify Razorpay signature
    is_valid = verify_payment_signature(
        razorpay_order_id,
        razorpay_payment_id,
        razorpay_signature
    )

    if not is_valid:
        txn.status = "FAILED"
        txn.save()
        return JsonResponse({"status": "failed"}, status=400)

   
    with transaction.atomic():
        wallet = txn.wallet

        txn.status = "COMPLETED"
        txn.transaction_id = razorpay_payment_id
        txn.save()

        wallet.balance += txn.amount
        wallet.save()

    return JsonResponse({"status": "success"})


@csrf_exempt
@login_required
def mark_wallet_payment_failed(request):
    if request.method == "POST":
        txn_id = request.POST.get("txn_id")
        if not txn_id:
            return JsonResponse({"status": "invalid_request"}, status=400)
            
        try:
            txn = WalletTransaction.objects.select_related("wallet").get(id=txn_id)
            if txn.wallet.user == request.user and txn.status == "PENDING":
                txn.status ="FAILED"
                txn.save()
                return JsonResponse({"status": "success"})
        except WalletTransaction.DoesNotExist:
            pass
        
    return JsonResponse({"status": "failed"}, status=400)


@never_cache
@login_required
def process_wallet_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Check if order is already processed
    if order.order_status != Order.Status.PENDING:
        messages.error(request, "This order cannot be processed.")
        return redirect("order_listing")

    payment = getattr(order, 'payment', None)
    if not payment:
        messages.error(request, "Invalid payment method.")
        return redirect("order_listing")

    # Prevent double payment
    if payment.payment_status == Payment.Status.SUCCESS:
        return redirect("order_success", order_id=order.id)

    wallet, created = Wallet.objects.get_or_create(user=request.user)

    if wallet.balance < order.total_amount:
        payment.payment_status = Payment.Status.FAILED
        payment.save()
        messages.error(request, "Insufficient wallet balance.")
        return redirect("payment_failed", order_id=order.id)

    try:
        with transaction.atomic():
            # Lock wallet for update
            wallet = Wallet.objects.select_for_update().get(id=wallet.id)
            
            if wallet.balance < order.total_amount:
                payment.payment_status = Payment.Status.FAILED
                payment.save()
                messages.error(request, "Insufficient wallet balance.")
                return redirect("payment_failed", order_id=order.id)

            # Deduct balance
            wallet.balance -= order.total_amount
            wallet.save()

            # Create wallet transaction
            WalletTransaction.objects.create(
                wallet=wallet,
                order=order,
                transaction_type='PURCHASE',
                amount=order.total_amount,
                status='COMPLETED',
                description=f"Payment for Order"
            )

            # Update Payment
            payment.payment_status = Payment.Status.SUCCESS
            payment.transaction_id = f"WALLET_{order.id}"
            payment.save()

            # Update Order
            order.order_status = Order.Status.CONFIRMED
            order.save()

            # Reduce stock 
            for item in order.items.all():
                variant = item.variant
                
                variant = Variant.objects.select_for_update().get(id=variant.id)
                if variant.stock < item.quantity:
                    raise Exception(f"Insufficient stock for {variant.product.name}")
                variant.stock -= item.quantity
                variant.save()

            # Log history
            OrderStatusHistory.objects.create(order=order, status=Order.Status.CONFIRMED)

            # Send confirmation email
            try:
                send_order_confirmation_email(request, order)
            except Exception:
                pass

        messages.success(request, "Payment successful using Wallet.")
        return redirect("order_success", order_id=order.id)
    except Exception as e:
        print("Wallet Payment Error:", e)
        payment.payment_status = Payment.Status.FAILED
        payment.save()
        messages.error(request, "Something went wrong during wallet payment.")
        return redirect("payment_failed",order_id=order.id)