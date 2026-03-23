from django import forms
from .models import Category

class CategoryForm(forms.ModelForm):
    
    class Meta:
        model=Category
        fields= ['name','is_active']
        
    def clean_name(self):
        name=self.cleaned_data.get('name','').strip()

        check=Category.objects.filter(name__iexact=name,is_deleted=False ).exists()
        
        # If editing exclude current object
        if self.instance.id:
            check.check.objects.exclude(id=self.instance.id)
            
        if check.exists():
            raise forms.ValidationError("Category already exists")

        return name