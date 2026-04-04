from django.db import models
from django.conf import settings
from product.models import Variant 

class Wishlist(models.Model):
    user=models.ForeignKey(
         settings.AUTH_USER_MODEL,on_delete=models.CASCADE,
        related_name='wishlist_items'
    )
    
    variant=models.ForeignKey(
        Variant, on_delete=models.CASCADE, related_name="wishlisted_by"
    )
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)   
    
    class Meta:
        unique_together =('user','variant')
        
    def __str__(self):
        return f"{self.user.username} - {self.variant.sku}"
        
class StockNotification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    variant = models.ForeignKey(
        Variant,
        on_delete=models.CASCADE
    )
    is_notified = models.BooleanField(default=False)  
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together =('user','variant')

    def __str__(self):
        return f"{self.user}-{self.variant}"
