from django import forms
from .models import Offer, OfferItem
from django.utils import timezone
import re
from decimal import Decimal

class OfferForm(forms.ModelForm):
    # We will handle these custom fields in the clean method if necessary
    apply_to = forms.CharField(required=False)
    product_id = forms.IntegerField(required=False)
    category_id = forms.IntegerField(required=False)

    class Meta:
        model = Offer
        fields = [
            "name",
            "discount_type",
            "discount_value",
            "max_discount",
            "min_purchase",
            "start_date",
            "end_date",
        ]

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        if not name:
            raise forms.ValidationError("Offer name is required")

        # Must start with a letter
        if not re.match(r'^[a-zA-Z]', name):
            raise forms.ValidationError("Offer name must start with a letter")

        # Must NOT be only numbers
        if name.isdigit():
            raise forms.ValidationError("Offer name cannot be only numbers")

        # Only letters + numbers + spaces allowed, No special characters
        if not re.match(r'^[a-zA-Z0-9\s]+$', name):
            raise forms.ValidationError("Offer name can only contain letters, numbers, and spaces")

        # Must be UNIQUE (case-insensitive)
        qs = Offer.objects.filter(name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("An offer with this name already exists")

        return name

    def clean_discount_value(self):
        val = self.cleaned_data.get("discount_value")
        if val is None:
            raise forms.ValidationError("Discount amount is required")
        
        if val <= 0:
            raise forms.ValidationError("Discount must be greater than 0")

        return val

    def clean_max_discount(self):
        val = self.cleaned_data.get("max_discount")
        if val is not None and val <= 0:
            raise forms.ValidationError("Max discount must be greater than 0")
        return val

    def clean_min_purchase(self):
        val = self.cleaned_data.get("min_purchase")
        if val is not None and val < 0:
            raise forms.ValidationError("Min purchase cannot be negative")
        return val

    def clean_start_date(self):
        start = self.cleaned_data.get("start_date")
        today = timezone.localtime().date()

        if start:
            # Handle start_date being a datetime object instead of date
            start_date_only = start.date() if hasattr(start, "date") else start
            if self.instance.pk:
                original_start_dt = timezone.localtime(self.instance.start_date) if timezone.is_aware(self.instance.start_date) else self.instance.start_date
                original_start_date = original_start_dt.date() if hasattr(original_start_dt, "date") else original_start_dt
                
                if start_date_only != original_start_date and start_date_only < today:
                    raise forms.ValidationError("Start date cannot be changed to a past date")
            else:
                if start_date_only < today:
                    raise forms.ValidationError("Start date cannot be in the past")
        return start

    def clean_end_date(self):
        end = self.cleaned_data.get("end_date")
        today = timezone.localtime().date()

        if end:
            end_date_only = end.date() if hasattr(end, "date") else end
            if self.instance.pk:
                if end_date_only < today:
                    raise forms.ValidationError("End date cannot be in the past. The offer would be expired immediately.")
            else:
                if end_date_only < today:
                    raise forms.ValidationError("End date cannot be in the past.")
        return end

    def clean(self):
        cleaned_data = super().clean()
        discount_type = cleaned_data.get("discount_type")
        discount_value = cleaned_data.get("discount_value")
        start = cleaned_data.get("start_date")
        end = cleaned_data.get("end_date")
        
        apply_to = cleaned_data.get("apply_to")
        product_id = cleaned_data.get("product_id")
        category_id = cleaned_data.get("category_id")

        if discount_type == "PERCENTAGE" and discount_value and discount_value > 100:
            self.add_error("discount_value", "Percentage discount cannot exceed 100%")

        if discount_type == "FLAT":
            cleaned_data["max_discount"] = None

        # Target Validation
        if not self.instance.pk:  # Only strict on creation for target, since edit doesn't change target usually
            if apply_to == "PRODUCT" and not product_id:
                self.add_error("product_id", "Select a product")
            if apply_to == "CATEGORY" and not category_id:
                self.add_error("category_id", "Select a category")

            now = timezone.now()
            # Duplicate Active Offer Check
            if apply_to == "PRODUCT" and product_id:
                exists = OfferItem.objects.filter(
                    product_id=product_id,
                    apply_to="PRODUCT",
                    offer__is_active=True,
                    offer__start_date__lte=now,
                    offer__end_date__gte=now,
                ).exists()
                if exists:
                    self.add_error("product_id", "This product already has an active offer")
            
            if apply_to == "CATEGORY" and category_id:
                exists = OfferItem.objects.filter(
                    category_id=category_id,
                    apply_to="CATEGORY",
                    offer__is_active=True,
                    offer__start_date__lte=now,
                    offer__end_date__gte=now,
                ).exists()
                if exists:
                    self.add_error("category_id", "This category already has an active offer")

        if start and end:
            start_date_only = start.date() if hasattr(start, "date") else start
            end_date_only = end.date() if hasattr(end, "date") else end
            
            if end_date_only <= start_date_only:
                self.add_error("end_date", "End date must be at least one day after the start date.")
            
            duration = (end_date_only - start_date_only).days
            if duration < 1:
                self.add_error("end_date", "Offer must run for at least 1 day.")
            if duration > 365:
                self.add_error("end_date", "Offer duration cannot exceed 1 year (365 days).")

        return cleaned_data
