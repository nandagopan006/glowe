from django.db import models
from django.conf import settings
from product.models import Variant
from user.models import Address
from order.models import Order,OrderItem

class ReturnRequest(models.Model):
    class Status(models.TextChoices):
        REQUESTED ="REQUESTED","Requested"
        APPROVED ="APPROVED","Approved"
        PICKUP_SCHEDULED ="PICKUP_SCHEDULED","Pickup Scheduled"
        PICKED_UP ="PICKED_UP","Picked Up"
        COMPLETED ="COMPLETED","Completed"
        REJECTED ="REJECTED","Rejected"

    order_item=models.ForeignKey(OrderItem,on_delete=models.CASCADE)
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    quantity=models.PositiveIntegerField(default=1)

    reason=models.CharField(max_length=255)
    description=models.TextField(blank=True)
    item_condition=models.CharField(max_length=100)

    return_status=models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.REQUESTED
    )

    pickup_date=models.DateTimeField(null=True,blank=True)
    picked_at=models.DateTimeField(null=True,blank=True)

    created_at=models.DateTimeField(auto_now_add=True)
    
class ReturnImage(models.Model):
    return_request=models.ForeignKey(ReturnRequest, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="returns/")