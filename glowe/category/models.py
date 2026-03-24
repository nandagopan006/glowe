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
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)

# Create your models here.
