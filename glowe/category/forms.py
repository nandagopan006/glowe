from django import forms
from .models import Category

class CategoryForm(forms.ModelForm):
    
    class Meta:
        model=Category
        fields= ['name','is_active']
        
    def clean_name(self):
        name=self.cleaned_data.get('name','').strip()

        qs=Category.objects.filter(name__iexact=name,is_deleted=False )
        
        # If editing exclude current object
        if self.instance and self.instance.id: 
            qs=qs.exclude(id=self.instance.id)
            
        if qs.exists():
            raise forms.ValidationError("Category already exists")

        return name