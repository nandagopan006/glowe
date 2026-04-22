from django.db import models
from product.models import Product
from category.models import Category

class Offer(models.Model):

    DISCOUNT_TYPE = (
        ("PERCENTAGE", "Percentage"),
        ("FLAT", "Flat"),
    )

    name =models.CharField(max_length=255)

    discount_type=models.CharField(max_length=20, choices=DISCOUNT_TYPE)

    discount_value= models.DecimalField(max_digits=10, decimal_places=2)

    max_discount=models.DecimalField(max_digits=10, decimal_places=2,
        null=True, blank=True
    )

    min_purchase = models.DecimalField(max_digits=10, decimal_places=2,null=True, blank=True)

    start_date =models.DateTimeField()
    end_date=models.DateTimeField()

    is_active=models.BooleanField(default=True)

    created_at=models.DateTimeField(auto_now_add=True)
    updated_at= models.DateTimeField(auto_now=True)
    

class OfferItem(models.Model):

    APPLY_TO = (
        ("PRODUCT", "Product"),
        ("CATEGORY", "Category"),
    )

    offer = models.ForeignKey(Offer,on_delete=models.CASCADE,related_name="items")

    apply_to=models.CharField(max_length=20, choices=APPLY_TO)

    product=models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        null=True, blank=True
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        null=True, blank=True
    )
    class Meta:
        unique_together = ("offer", "product", "category")
