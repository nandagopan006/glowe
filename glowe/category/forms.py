from django import forms
from .models import Category


class CategoryForm(forms.ModelForm):

    class Meta:
        model = Category
        fields = ["name", "is_active"]

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()

        if not name:
            raise forms.ValidationError("Category name is required.")

        # Must start with a letter
        import re
        if not re.match(r'^[a-zA-Z]', name):
            raise forms.ValidationError("Category name must start with a letter.")

        if name.isdigit():
            raise forms.ValidationError("Category name cannot be only numbers.")

       
        if not re.match(r'^[a-zA-Z0-9\s]+$', name):
            raise forms.ValidationError("Category name can only contain letters, numbers, and spaces.")

        # Must be UNIQUE (case-insensitive)
        qs = Category.objects.filter(name__iexact=name, is_deleted=False)

        # If editing exclude current object
        if self.instance and self.instance.id:
            qs = qs.exclude(id=self.instance.id)

        if qs.exists():
            raise forms.ValidationError("Category already exists.")

        # Convert to UPPERCASE before saving
        return name.upper()
