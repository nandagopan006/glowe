from django.db import models
from django.utils.text import slugify

class Category(models.Model):
    name=models.CharField(max_length=100)
    slug=models.SlugField(unique=True,blank=True)
    is_active=models.BooleanField(default=True)
    is_deleted=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        base_slug = slugify(self.name)
        slug = base_slug
        counter = 1

        while Category.objects.filter(slug=slug).exclude(id=self.id).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        self.slug = slug
        super().save(*args, **kwargs)


# Create your models here.
