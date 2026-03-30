from django.db import models
from django.conf import settings
from product.models import Variant,Product


class Cart(models.Model):
    user=models.ForeignKey(
        settings.AUTH_USER_MODEL,  
        on_delete=models.CASCADE,
        related_name='carts'
    )
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)


class CartItem(models.Model):
    cart=models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items'
    )
    variant=models.ForeignKey(Variant, on_delete=models.CASCADE)
    quantity=models.PositiveIntegerField(default=1)

    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)