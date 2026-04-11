from django.urls import path
from . import views


urlpatterns = [
path("payment/<int:order_id>/",views.payment_page, name="payment_page"),
path("verify-payment/", views.verify_payment, name="verify_payment"),
path("payment-failed/<int:order_id>/", views.payment_failed, name="payment_failed"),
]