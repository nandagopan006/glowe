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
    
class OrderItem(models.Model):
    class Status(models.TextChoices):
        PENDING="PENDING","Pending"
        SHIPPED ="SHIPPED","Shipped"
        DELIVERED= "DELIVERED","Delivered"
        CANCELLED="CANCELLED","Cancelled"
        RETURN_REQUESTED = "RETURN_REQUESTED", "Return Requested"

    order=models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    variant=models.ForeignKey(Variant, on_delete=models.CASCADE)

    price_at_time=models.DecimalField(max_digits=10, decimal_places=2)
    quantity= models.PositiveIntegerField()

    item_status=models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    cancel_reason=models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.variant} - {self.quantity}"

class ShippingAddress(models.Model):

    order=models.OneToOneField(Order, on_delete=models.CASCADE, related_name="shipping_address")
    user=models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    full_name=models.CharField(max_length=100)
    phone=models.CharField(max_length=10)

    address_line1=models.TextField()
    city=models.CharField(max_length=100)
    district=models.CharField(max_length=100)
    state=models.CharField(max_length=100)
    country=models.CharField(max_length=100, default="India")
    pincode=models.CharField(max_length=6)
    
class Payment(models.Model):

    class Method(models.TextChoices):
        COD ="COD", "Cash on Delivery"
        RAZORPAY = "RAZORPAY", "Razorpay"
    class Status(models.TextChoices):
        PENDING="PENDING","Pending"
        SUCCESS="SUCCESS", "Success"
        FAILED ="FAILED", "Failed"

    order = models.OneToOneField(Order, on_delete=models.CASCADE)

    payment_method=models.CharField(
        max_length=20,
        choices=Method.choices,
        default=Method.COD
    )

    transaction_id=models.CharField(max_length=100, blank=True, null=True)
    amount =models.DecimalField(max_digits=10, decimal_places=2)

    payment_status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    created_at = models.DateTimeField(auto_now_add=True)
    
class OrderStatusHistory(models.Model):

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_history")
    status = models.CharField(max_length=30)
    updated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.order.order_number} - {self.status}"