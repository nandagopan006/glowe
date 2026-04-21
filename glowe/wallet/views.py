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



def wallet_view(request):
    wallet,created = Wallet.objects.get_or_create(user=request.user)

    transactions_list = wallet.transactions.all().order_by('-created_at')

    paginator=Paginator(transactions_list,5)  # 5 per page
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