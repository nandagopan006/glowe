from django import forms
from .models import Coupon
from django.utils import timezone

class CouponForm(forms.ModelForm):
    class Meta:
        model = Coupon
        exclude = ['used_count', 'is_deleted']

    def clean_code(self):
        code =self.cleaned_data.get('code')

        if code:
            code=code.upper().strip()

            # prevent duplicate
            qs=Coupon.objects.filter(code__iexact=code, is_deleted=False)
            if self.instance.pk:
                qs=qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise forms.ValidationError("Coupon code already exists")

        return code

    def clean(self):
        cleaned = super().clean()

        dtype=cleaned.get('discount_type')
        value=cleaned.get('discount_value')
        min_purchase =cleaned.get('min_purchase')
        max_discount=cleaned.get('max_discount')
        total_limit=cleaned.get('total_usage_limit')
        per_user_limit=cleaned.get('usage_limit_per_user')
        start=cleaned.get('start_date')
        end=cleaned.get('end_date')

        today=timezone.now().date()

        if start and start < today:
            raise forms.ValidationError("Start date cannot be in the past")

        if start and end:
            if start > end:
                raise forms.ValidationError("End date must be after start date")

        if end and end < today:
            raise forms.ValidationError("End date cannot be in the past")

        if dtype == 'percentage':
            if not value or value <= 0:
                raise forms.ValidationError("Percentage must be greater than 0")

            if value > 100:
                raise forms.ValidationError("Percentage cannot exceed 100")

            if not max_discount or max_discount <= 0:
                raise forms.ValidationError("Max discount required for percentage coupon")

        elif dtype == 'flat':
            if not value or value <= 0:
                raise forms.ValidationError("Flat discount must be greater than 0")

            # above 20000 not alloow
            if value > 20000:
                raise forms.ValidationError("Flat discount too large")

            # remove max_discount if mistakenly added
            cleaned['max_discount'] = None

        if min_purchase is not None:
            if min_purchase < 0:
                raise forms.ValidationError("Minimum purchase cannot be negative")

        if max_discount is not None:
            if max_discount < 0:
                raise forms.ValidationError("Max discount cannot be negative")

        #usge limit
        if total_limit is not None:
            if total_limit <= 0:
                raise forms.ValidationError("Total usage must be greater than 0")

        if per_user_limit is not None:
            if per_user_limit <= 0:
                raise forms.ValidationError("Limit per user must be at least 1")

        if total_limit and per_user_limit:
            if per_user_limit > total_limit:
                raise forms.ValidationError("Per user limit cannot exceed total limit")

        return cleaned
        