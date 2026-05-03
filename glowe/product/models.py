from django.db import models
from django.utils.text import slugify
from category.models import Category
from .utils import resize_image


class Product(models.Model):
    """
    Represents a product in the catalog.
    """
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )

    description = models.TextField()
    ingredients = models.TextField()
    how_to_use = models.TextField()
    skin_type = models.CharField(max_length=100, blank=True)

    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1

            while (
                Product.objects.filter(slug=slug).exclude(id=self.id).exists()
            ):
                slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = slug

        super().save(*args, **kwargs)


class ProductImage(models.Model):
    """
    Stores images associated with a Product.
    """
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images"
    )

    image = models.ImageField(upload_to="products/")
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.image:
            resize_image(self.image.path)


class Variant(models.Model):
    """
    Represents a specific size or type of a Product with its own
    price and stock.
    """
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="variants"
    )

    size = models.CharField(max_length=20)  # 30ml,100g
    sku = models.CharField(max_length=100, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField()

    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):

        base_sku = f"{self.product.slug}-{self.size}".upper()
        sku = base_sku
        counter = 1

        while Variant.objects.filter(sku=sku).exclude(id=self.id).exists():
            sku = f"{base_sku}-{counter}"
            counter += 1

        self.sku = sku

        if self.is_default:
            Variant.objects.filter(product=self.product).exclude(
                id=self.id
            ).update(is_default=False)

        super().save(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=["sku"]),
            models.Index(fields=["price"]),
            models.Index(fields=["created_at"]),
        ]
