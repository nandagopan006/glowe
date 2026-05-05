from django import forms
from .models import Coupon
from django.utils import timezone
import re


class CouponForm(forms.ModelForm):
    class Meta:
        model = Coupon
        exclude = ["used_count", "is_deleted"]

    def clean_code(self):
        code = self.cleaned_data.get("code")

        if code:
            code = code.upper().strip()

            # Validation: Must not be empty after stripping
            if not code:
                raise forms.ValidationError("Coupon code cannot be empty")

            # Validation: Must NOT be only numbers
            if code.isdigit():
                raise forms.ValidationError(
                    "Coupon code cannot contain only numbers"
                )

            # Validation: Must be alphanumeric (letters + numbers, optional hyphen/underscore)
            if not re.match(r'^[A-Z0-9_-]+$', code):
                raise forms.ValidationError(
                    "Coupon code must be alphanumeric (letters, numbers, hyphen, or underscore only)"
                )

            # Validation: Must contain at least one letter
            if not re.search(r'[A-Z]', code):
                raise forms.ValidationError(
                    "Coupon code must contain at least one letter"
                )

            # Validation: Length check (reasonable limits)
            if len(code) < 3:
                raise forms.ValidationError(
                    "Coupon code must be at least 3 characters long"
                )
            if len(code) > 50:
                raise forms.ValidationError(
                    "Coupon code cannot exceed 50 characters"
                )

            # Validation: Prevent duplicate (case insensitive)
            qs = Coupon.objects.filter(code__iexact=code, is_deleted=False)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise forms.ValidationError(
                    "This coupon code already exists"
                )

        return code

    def clean_discount_value(self):
        """Validate discount value field"""
        value = self.cleaned_data.get("discount_value")
        
        if value is None:
            raise forms.ValidationError("Discount amount is required")
        
        if value <= 0:
            raise forms.ValidationError("Discount must be greater than 0")
        
        return value

    def clean_start_date(self):
        """Validate start date"""
        start = self.cleaned_data.get("start_date")
        today = timezone.now().date()

        if start:
            if self.instance.pk:
                # When editing, only check if the date was changed
                if start != self.instance.start_date and start < today:
                    raise forms.ValidationError("Start date cannot be changed to a past date")
            else:
                if start < today:
                    raise forms.ValidationError("Start date cannot be in the past")
        
        return start

    def clean_end_date(self):
        """Validate end date"""
        end = self.cleaned_data.get("end_date")
        today = timezone.now().date()

        if end:
            if self.instance.pk:
                if end != self.instance.end_date and end < today:
                    raise forms.ValidationError("End date cannot be changed to a past date")
            else:
                if end < today:
                    raise forms.ValidationError("End date cannot be in the past")
        
        return end

    def clean(self):
        cleaned = super().clean()

        dtype = cleaned.get("discount_type")
        value = cleaned.get("discount_value")
        min_purchase = cleaned.get("min_purchase")
        max_discount = cleaned.get("max_discount")
        total_limit = cleaned.get("total_usage_limit")
        per_user_limit = cleaned.get("usage_limit_per_user")
        start = cleaned.get("start_date")
        end = cleaned.get("end_date")

        # Date validation
        if start and end:
            if start > end:
                raise forms.ValidationError(
                    "End date must be after start date"
                )

        # Discount type specific validation
        if dtype == "percentage":
            if value and value > 100:
                raise forms.ValidationError("Percentage cannot exceed 100")

            if not max_discount or max_discount <= 0:
                raise forms.ValidationError(
                    "Max discount cap is required for percentage coupons"
                )

        elif dtype == "flat":
            # Flat discount upper limit
            if value and value > 20000:
                raise forms.ValidationError(
                    "Flat discount cannot exceed ₹20,000"
                )

            # Remove max_discount if mistakenly added for flat
            cleaned["max_discount"] = None

        # Min purchase validation
        if min_purchase is not None:
            if min_purchase < 0:
                raise forms.ValidationError(
                    "Minimum purchase cannot be negative"
                )
            if min_purchase > 1000000:
                raise forms.ValidationError(
                    "Minimum purchase amount is too large"
                )

        # Max discount validation
        if max_discount is not None:
            if max_discount < 0:
                raise forms.ValidationError("Max discount cannot be negative")
            if max_discount > 50000:
                raise forms.ValidationError(
                    "Max discount cap is too large"
                )

        # Usage limit validation
        if total_limit is not None:
            if total_limit <= 0:
                raise forms.ValidationError(
                    "Total usage limit must be greater than 0"
                )
            if total_limit > 1000000:
                raise forms.ValidationError(
                    "Total usage limit is too large"
                )

        if per_user_limit is not None:
            if per_user_limit <= 0:
                raise forms.ValidationError(
                    "Per user limit must be at least 1"
                )
            if per_user_limit > 1000:
                raise forms.ValidationError(
                    "Per user limit is too large"
                )

        # Cross-field validation
        if total_limit and per_user_limit:
            if per_user_limit > total_limit:
                raise forms.ValidationError(
                    "Per user limit cannot exceed total usage limit"
                )

        return cleaned
