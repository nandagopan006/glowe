from django import forms
from .models import Product, Variant
import re

class ProductForm(forms.ModelForm):
    
    class Meta:
        model =Product
        fields =[
            'name','category',
            "description","ingredients",
            'how_to_use','skin_type'
        ]
    def clean_name(self):
        
        name=self.cleaned_data.get('name','').strip()
        if not name:
            raise forms.ValidationError("Product name is required.")
        
        qs=Product.objects.filter(name__iexact=name)
        if self.instance.id:                     # editing existing product
            qs = qs.exclude(pk=self.instance.id) # ignore itself
        if qs.exists():
            raise forms.ValidationError("Product with this name already exists.")
        if len(name)< 3 :
            raise forms.ValidationError("Product name too short")  
        
        return name 
    
    def clean_description(self):
        description=self.cleaned_data.get('description','').strip()
        
        if len(description) < 12 :
            raise forms.ValidationError('description need more than 12chars')
        
        return description
    
    def clean_ingredients(self):
        ingredients = self.cleaned_data.get('ingredients', '').strip()

        if ingredients:
            if len(ingredients) < 5:
                raise forms.ValidationError("Ingredients too short")

        return ingredients

    def clean_how_to_use(self):
        how =self.cleaned_data.get('how_to_use','').strip()

        if how:
            if len(how) < 5:
                raise forms.ValidationError("How to use is too short")

        return how
    def clean_skin_type(self):
        skin_type=self.cleaned_data.get('skin_type','').strip()
        
        if skin_type:
            pattern=r'^[A-Za-z\s&,-]+$'
            
            if not re.match(pattern,skin_type):
                raise forms.ValidationError("Only letters, spaces, &, -, and commas allowed.")
        return skin_type
    
    
class VariantForm(forms.ModelForm):
    class Meta:
        model=Variant
        fields= ['size','price','stock','is_default']
    
    def clean_size(self):
        size=self.cleaned_data.get('size','').strip().lower().replace(' ','')
        
        if not size :
            raise forms.ValidationError("Size is required")
        # 30ml or 50g
        pattern =r'^\d+(ml|g)$'  
        if not re.match(pattern, size):
            raise forms.ValidationError("Size must be like 30ml or 50g")
        
        product = self.instance.product if self.instance.pk else self.initial.get('product')

        if Variant.objects.filter(product=product, size=size).exclude(id=self.instance.id).exists():
            raise forms.ValidationError("Variant with this size already exists.")
        
        return size.lower()
        
    
    def clean_price(self):
        price=self.cleaned_data.get('price')
        
        if price is None or price <= 0 :
            raise forms.ValidationError("Price must be greater than 0")
        
        if price > 10000:
            raise forms.ValidationError("Price exceeds allowed limit")
        
        return price
    
    def clean_stock(self):
        stock=self.cleaned_data.get('stock')
        
        if stock is None or stock < 0:
            raise forms.ValidationError("Stock cannot be negative")
        
        if stock > 10000:
            raise forms.ValidationError("Stock too large")

        return stock
        
    def clean(self):
        
        cleaned_data =super().clean()
        size=cleaned_data.get('size')

        if size and getattr(self.instance,"product",None):
            exists=Variant.objects.filter(product=self.instance.product,size=size
                                          ).exclude(id=self.instance.id).exists()

            if exists:
                raise forms.ValidationError("This size already exists for this product")

        return cleaned_data
            
        
    
    
        
        
        