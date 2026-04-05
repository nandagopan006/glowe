from django.db import models
from django.conf import settings
from product.models import Variant
from user.models import Address
class Order(models.Model):
    class Status(models.TextChoices):
        PENDING ="PENDING","Pending"
        CONFIRMED="CONFIRMED","Confirmed"
        PROCESSING= "PROCESSING","Processing"
        SHIPPED="SHIPPED","Shipped"
        OUT_FOR_DELIVERY="OUT_FOR_DELIVERY","Out for Delivery"
        DELIVERED= "DELIVERED","Delivered"
        CANCELLED ="CANCELLED","Cancelled"

    user=models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    order_number=models.CharField(max_length=20,unique=True)
    address=models.ForeignKey(Address,on_delete=models.SET_NULL, null=True)

    subtotal=models.DecimalField(max_digits=10, decimal_places=2)
    delivery_charge=models.DecimalField(max_digits=10,decimal_places=2,default=0)
    discount_amount=models.DecimalField(max_digits=10,decimal_places=2,default=0)

    total_amount=models.DecimalField(max_digits=10, decimal_places=2)

    order_status=models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING
    )

    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    delivered_date=models.DateTimeField(null=True,blank=True)

    def __str__(self):
        return self.order_number