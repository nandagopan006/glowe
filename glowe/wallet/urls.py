from django.urls import path
from . import views

urlpatterns = [
    path("wallet-view/", views.wallet_view, name="wallet_view"),
    path("wallet/create-order/", views.create_wallet_order, name="wallet_create_order"),
    path("wallet/verify-payment/", views.verify_wallet_payment, name="wallet_verify_payment"),
]
