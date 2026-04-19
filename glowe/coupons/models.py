from django.db import models
from django.conf import settings
class Coupon(models.Model):

    DISCOUNT_TYPE_CHOICES =(
        ('percentage','Percentage'),('flat','Flat'),
        )

    code=models.CharField(max_length=50, unique=True)

    discount_type =models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES)
    discount_value =models.DecimalField(max_digits=10, decimal_places=2)

    min_purchase=models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_discount=models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    total_usage_limit =models.IntegerField(null=True, blank=True)
    usage_limit_per_user=models.IntegerField(default=1)

    used_count =models.IntegerField(default=0)

    start_date =models.DateField()
    end_date = models.DateField()

    is_active=models.BooleanField(default=True)
    is_deleted=models.BooleanField(default=False)

    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    
    
    
class CouponUsage(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    coupon=models.ForeignKey(Coupon,on_delete=models.CASCADE)
    used_count=models.IntegerField(default=0)

    class Meta:
        unique_together=('user', 'coupon')