from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from .models import Coupon
from django.db import models
from .forms import CouponForm

def coupon_list(request):
    coupons=Coupon.objects.filter(is_deleted=False).order_by('-created_at')

    search =request.GET.get('search')
    if search:
        coupons=coupons.filter(code__icontains=search)

    status_filter =request.GET.get('status')
    today = timezone.now().date()

    if status_filter == "active":
        coupons= coupons.filter(is_active=True, end_date__gte=today)

    elif status_filter == "expired":
        coupons=coupons.filter(end_date__lt=today)

    elif status_filter == "inactive":
        coupons = coupons.filter(is_active=False, end_date__gte=today)

    paginator = Paginator(coupons,4)
    page =request.GET.get('page')
    coupons=paginator.get_page(page)

    for c in coupons:
        # status
        if c.end_date < today:
            c.status = "Expired"
            
        elif not c.is_active:
            c.status = "Inactive"
            
        else:
            c.status = "Active"

        # usage 
        if c.total_usage_limit and c.total_usage_limit > 0:
            c.usage_percent = int((c.used_count / c.total_usage_limit) * 100)
        else:
            c.usage_percent = 0

    total_active = Coupon.objects.filter(is_active=True,is_deleted=False,
                                         end_date__gte=today).count()

    total_used = Coupon.objects.filter(is_deleted=False).aggregate(total=models.Sum('used_count'))['total'] or 0

    return render(request,'admin/coupons_list.html',{
        'coupons':coupons,
        'search':search,
        'total_active':total_active,
        'total_used':total_used
    })
    
def create_coupon(request):
    if request.method == "POST":
        form =CouponForm(request.POST)

        if form.is_valid():
            coupon =form.save(commit=False)

            coupon.code=coupon.code.upper().strip()
            coupon.used_count=0

            coupon.save()

            messages.success(request, f"Coupon '{coupon.code}' created ")
        else:
            messages.error(request, "Please fix form errors ")

    return redirect('coupon_list')
