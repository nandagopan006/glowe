from django.db import models
from django.utils.text import slugify
from category.models import Category 


class Product(models.Model):
    name=models.CharField(max_length=200)
    slug=models.SlugField(unique=True)

    category=models.ForeignKey(Category, on_delete=models.CASCADE)

    description=models.TextField()
    ingredients=models.TextField()
    how_to_use=models.TextField()
    skin_type=models.CharField(max_length=100, blank=True)

    is_active=models.BooleanField(default=True)
    is_deleted=models.BooleanField(default=False)

    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    
    def save(self,*args,**kwargs):
        if not self.slug:
            self.slug =slugify(self.name)
        super().save(*args,**kwargs)
    
    
class ProductImage(models.Model):
    product=models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')

    image=models.ImageField(upload_to='products/')
    is_primary=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
    
    class Meta :
        ordering=['id']
    
class Variant(models.Model):
    product=models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')

    size=models.CharField(max_length=20)  # 30ml,100g
    sku=models.CharField(max_length=100, unique=True)
    price=models.DecimalField(max_digits=10, decimal_places=2)
    stock=models.PositiveIntegerField()

    is_default=models.BooleanField(default=False)
    is_active=models.BooleanField(default=True)
    created_at =models.DateTimeField(auto_now_add=True)
    
    def save(self,*args,**kwargs):
        if not self.sku:
            self.sku=f"{self.product.slug}-{self.size}".upper()
        super().save(*args, **kwargs)