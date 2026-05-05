from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from .models import Coupon, CouponUsage
from django.db import models
from .forms import CouponForm
from cart.utils import get_cart_total
from decimal import Decimal
from django.views.decorators.cache import never_cache
from core.decorators import admin_required
from django.contrib.auth.decorators import login_required


@never_cache
@admin_required
def coupon_list(request):
    status = request.GET.get("status", "live")
    search = request.GET.get("search", "")
    active_status = request.GET.get("active_status", "")
    today = timezone.now().date()

    if status == "archived":
        coupons = Coupon.objects.filter(is_deleted=True).order_by(
            "-created_at"
        )
    else:
        coupons = Coupon.objects.filter(is_deleted=False).order_by(
            "-created_at"
        )
        if active_status == "active":
            coupons = coupons.filter(is_active=True, end_date__gte=today)
        elif active_status == "inactive":
            coupons = coupons.filter(
                models.Q(is_active=False) | models.Q(end_date__lt=today)
            )

    if search:
        coupons = coupons.filter(code__icontains=search)

    paginator = Paginator(coupons, 4)
    page = request.GET.get("page")
    coupons_page = paginator.get_page(page)

    for c in coupons_page:
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

    total_active = Coupon.objects.filter(
        is_active=True, is_deleted=False, end_date__gte=today
    ).count()
    total_used = (
        Coupon.objects.filter(is_deleted=False).aggregate(
            total=models.Sum("used_count")
        )["total"]
        or 0
    )
    archived_count = Coupon.objects.filter(is_deleted=True).count()
    total_coupons = Coupon.objects.filter(is_deleted=False).count()

    return render(
        request,
        "coupons_list.html",
        {
            "coupons": coupons_page,
            "search": search,
            "status": status,
            "active_status": active_status,
            "total_active": total_active,
            "total_used": total_used,
            "archived_count": archived_count,
            "total_coupons": total_coupons,
        },
    )


@never_cache
@admin_required
def create_coupon(request):
    if request.method == "POST":
        # Check if it's an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        form = CouponForm(request.POST)

        if form.is_valid():
            coupon = form.save(commit=False)
            coupon.used_count = 0
            coupon.save()

            if is_ajax:
                return JsonResponse({
                    "success": True,
                    "message": f"Coupon '{coupon.code}' created successfully"
                })
            else:
                messages.success(request, f"Coupon '{coupon.code}' created")
                return redirect("coupon_list")
        else:
            # Handle validation errors
            if is_ajax:
                # Format errors for JSON response
                errors = {}
                
                # Field-specific errors
                for field, error_list in form.errors.items():
                    if field == '__all__':
                        # Non-field errors (from clean() method)
                        errors['non_field_errors'] = [str(e) for e in error_list]
                    else:
                        errors[field] = [str(e) for e in error_list]
                
                return JsonResponse({
                    "success": False,
                    "errors": errors
                })
            else:
                messages.error(request, "Please fix form errors")
                return redirect("coupon_list")

    return redirect("coupon_list")


@never_cache
@admin_required
def edit_coupon(request, id):
    coupon = get_object_or_404(Coupon, id=id, is_deleted=False)

    if request.method == "POST":
        # Check if it's an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        form = CouponForm(request.POST, instance=coupon)

        if form.is_valid():
            updated_coupon = form.save(commit=False)
            updated_coupon.code = updated_coupon.code.upper().strip()
            updated_coupon.save()

            if is_ajax:
                return JsonResponse({
                    "success": True,
                    "message": "Coupon updated successfully"
                })
            else:
                messages.success(request, "Coupon updated successfully")
                return redirect("coupon_list")
        else:
            # Handle validation errors
            if is_ajax:
                # Format errors for JSON response
                errors = {}
                
                # Field-specific errors
                for field, error_list in form.errors.items():
                    if field == '__all__':
                        # Non-field errors (from clean() method)
                        errors['non_field_errors'] = [str(e) for e in error_list]
                    else:
                        errors[field] = [str(e) for e in error_list]
                
                return JsonResponse({
                    "success": False,
                    "errors": errors
                })
            else:
                messages.error(request, "Please fix the errors")
                return redirect("coupon_list")

    return redirect("coupon_list")


@never_cache
@admin_required
def delete_coupon(request, id):
    coupon = get_object_or_404(Coupon, id=id, is_deleted=False)

    if request.method == "POST":
        coupon.is_deleted = True
        coupon.save()
        messages.success(request, f"Coupon '{coupon.code}' moved to archive.")

    return redirect("coupon_list")


@never_cache
@admin_required
def restore_coupon(request, id):
    coupon = get_object_or_404(Coupon, id=id, is_deleted=True)

    if request.method == "POST":
        coupon.is_deleted = False
        coupon.save()
        messages.success(
            request, f"Coupon '{coupon.code}' restored successfully."
        )

    return redirect("coupon_list")


@never_cache
@admin_required
def permanent_delete_coupon(request, id):
    coupon = get_object_or_404(Coupon, id=id, is_deleted=True)

    if request.method == "POST":
        code = coupon.code
        coupon.delete()
        messages.success(request, f"Coupon '{code}' permanently deleted.")

    return redirect("coupon_list")


@never_cache
@admin_required
def toggle_coupon(request, id):
    coupon = get_object_or_404(Coupon, id=id, is_deleted=False)

    if request.method == "POST":

        today = timezone.now().date()

        # prevent activating expired coupon
        if coupon.end_date < today:
            messages.error(request, "Cannot activate expired coupon ")
            return redirect("coupon_list")

        if (
            coupon.total_usage_limit
            and coupon.used_count >= coupon.total_usage_limit
        ):
            messages.error(request, "Coupon usage limit reached ")
            return redirect("coupon_list")

        coupon.is_active = not coupon.is_active
        coupon.save()

        if coupon.is_active:
            messages.success(request, "Coupon activated")
        else:
            messages.success(request, "Coupon deactivated")

    return redirect("coupon_list")


# ----- - - - -  user side------


@login_required
def apply_coupon(request):
    if request.method == "POST":
        code = request.POST.get("code")
        if not code:
            return JsonResponse(
                {"success": False, "message": "Enter coupon code"}
            )

        code = code.strip().upper()
        user = request.user
        today = timezone.now().date()

        # get cart total
        cart_total = get_cart_total(user)

        try:
            coupon = Coupon.objects.get(code=code, is_deleted=False)
        except Coupon.DoesNotExist:
            return JsonResponse(
                {"success": False, "message": "Invalid coupon code"}
            )

        # Validation
        if not coupon.is_active:
            return JsonResponse(
                {
                    "success": False,
                    "message": "This coupon is currently inactive",
                }
            )

        if coupon.start_date > today:
            return JsonResponse(
                {
                    "success": False,
                    "message": f"Coupon starts on {coupon.start_date}",
                }
            )

        if coupon.end_date < today:
            return JsonResponse(
                {"success": False, "message": "This coupon has expired"}
            )

        if (
            coupon.total_usage_limit
            and coupon.used_count >= coupon.total_usage_limit
        ):
            return JsonResponse(
                {"success": False, "message": "Coupon usage limit reached"}
            )

        # Per user limit
        usage = CouponUsage.objects.filter(user=user, coupon=coupon).first()
        if usage and usage.used_count >= coupon.usage_limit_per_user:
            return JsonResponse(
                {
                    "success": False,
                    "message": "You have already used this coupon",
                }
            )

        # Min purchase
        if coupon.min_purchase and cart_total < coupon.min_purchase:
            return JsonResponse(
                {
                    "success": False,
                    "message": f"Minimum purchase of ₹{coupon.min_purchase} required",  # noqa: E501
                }
            )

        # Success - Save in session
        request.session["coupon_id"] = coupon.id
        request.session["coupon_code"] = coupon.code
        return JsonResponse(
            {
                "success": True,
                "message": f'Coupon "{coupon.code}" applied successfully!',
            }
        )
    return JsonResponse({"success": False, "message": "Invalid request"})


def remove_coupon(request):
    if "coupon_id" in request.session:
        del request.session["coupon_id"]
    if "coupon_code" in request.session:
        del request.session["coupon_code"]
    return JsonResponse({"success": True, "message": "Coupon removed"})


def calculate_discount(request, cart_total):
    coupon_id = request.session.get("coupon_id")
    if not coupon_id:
        return Decimal("0.00")

    try:
        coupon = Coupon.objects.get(
            id=coupon_id, is_active=True, is_deleted=False
        )
        today = timezone.now().date()

        # Double check validity
        if coupon.start_date > today or coupon.end_date < today:
            del request.session["coupon_id"]
            return Decimal("0.00")

        if (
            coupon.total_usage_limit
            and coupon.used_count >= coupon.total_usage_limit
        ):
            del request.session["coupon_id"]
            return Decimal("0.00")

        if request.user.is_authenticated:

            usage = CouponUsage.objects.filter(
                user=request.user, coupon=coupon
            ).first()
            if usage and usage.used_count >= coupon.usage_limit_per_user:
                del request.session["coupon_id"]
                return Decimal("0.00")

        if coupon.min_purchase and cart_total < coupon.min_purchase:
            return Decimal("0.00")

        if coupon.discount_type == "percentage":
            discount = (coupon.discount_value / Decimal("100")) * Decimal(
                cart_total
            )
            if coupon.max_discount:
                discount = min(discount, coupon.max_discount)
        else:
            discount = coupon.discount_value

        return Decimal(discount)
    except Coupon.DoesNotExist:
        if "coupon_id" in request.session:
            del request.session["coupon_id"]
        return Decimal("0.00")
