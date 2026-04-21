from django.shortcuts import render
from django.core.paginator import Paginator
from .models import Wallet


def wallet_view(request):
    wallet,created = Wallet.objects.get_or_create(user=request.user)

    transactions_list = wallet.transactions.all().order_by('-created_at')

    paginator=Paginator(transactions_list,5)  # 5 per page
    page_number=request.GET.get('page')
    transactions =paginator.get_page(page_number)

    return render(request,'wallet/wallet.html',{
        'wallet':wallet,
        'transactions':transactions
    })