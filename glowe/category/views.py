from django.shortcuts import render, redirect, get_object_or_404
from .forms import CategoryForm
from django.contrib import messages

from .models import Category
from django.db.models import Count
from django.core.paginator import Paginator
from django.views.decorators.cache import never_cache
from core.decorators import admin_required


@never_cache
@admin_required
def category_management(request):

    q = request.GET.get("q", "").strip()
    active_status = request.GET.get("active_status", "")
    status = request.GET.get("status", "live")

    qs = Category.objects.all().annotate(product_count=Count("products"))

    if q:
        qs = qs.filter(name__icontains=q)

    if active_status == "active":
        qs = qs.filter(is_active=True)
    elif active_status == "inactive":
        qs = qs.filter(is_active=False)

    if status == "archived":
        qs = qs.filter(is_deleted=True)
    else:
        qs = qs.filter(is_deleted=False)

    # sort
    qs = qs.order_by("-created_at")

    paginator = Paginator(qs, 5)
    page_number = request.GET.get("page")
    categories = paginator.get_page(page_number)

    total = Category.objects.filter(is_deleted=False).count()
    active = Category.objects.filter(is_active=True, is_deleted=False).count()
    inactive = Category.objects.filter(
        is_active=False, is_deleted=False
    ).count()
    archived_count = Category.objects.filter(is_deleted=True).count()
    context = {
        "query": q,
        "categories": categories,
        "status": status,
        "active_status": active_status,
        "total_categories": total,
        "active_categories": active,
        "inactive_categories": inactive,
        "archived_count": archived_count,
    }

    return render(request, "category_management.html", context)


@never_cache
@admin_required
def add_category(request):

    if request.method == "POST":
        form = CategoryForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "category is created successfully")
            return redirect("category_management")

        else:

            # If form invalid, show errors
            for errors in form.errors.values():
                for e in errors:
                    messages.error(request, e)

    return redirect("category_management")


@never_cache
@admin_required
def edit_category(request, id):

    category = get_object_or_404(Category, id=id, is_deleted=False)

    if request.method == "POST":
        form = CategoryForm(request.POST, instance=category)

        if form.is_valid():
            form.save()
            messages.success(request, "category successfully updated....")
        else:
            for errors in form.errors.values():
                for e in errors:
                    messages.error(request, e)

    return redirect("category_management")


@never_cache
@admin_required
def toggle_category(request, id):

    if request.method != "POST":
        return redirect("category_management")

    category = get_object_or_404(Category, id=id)

    if category.is_deleted:
        messages.error(request, "Cannot modify archived category")
        return redirect("category_management")

    category.is_active = not category.is_active
    category.save()
    active_status = "activated" if category.is_active else "deactivated"
    messages.success(request, f"{category.name}  has been {active_status}.")
    return redirect("category_management")


@never_cache
@admin_required
def soft_delete_category(request, id):
    if request.method == "POST":
        category = get_object_or_404(Category, id=id)
        if category.is_deleted:
            messages.error(request, "Category already archived")
            return redirect("category_management")

        # Count affected active products
        affected = category.products.filter(is_deleted=False, is_active=True).count()

        category.is_deleted = True
        category.is_active = False  # Also deactivate so it disappears from nav
        category.save()

        if affected > 0:
            messages.warning(
                request,
                f"'{category.name}' archived. {affected} product(s) are now hidden from the storefront. "
                f"Restore the category to make them visible again."
            )
        else:
            messages.success(request, f"'{category.name}' has been archived.")
        return redirect("category_management")
    return redirect("category_management")


@never_cache
@admin_required
def restore_category(request, id):
    if request.method == "POST":
        category = get_object_or_404(Category, id=id, is_deleted=True)

        category.is_deleted = False
        category.is_active = True  # Re-activate when restoring
        category.save()

        # Count products now visible again
        restored_products = category.products.filter(
            is_deleted=False, is_active=True
        ).count()

        # Trigger stock notifications for any subscribers
        # (products become visible again when category is restored)
        from product.signals import _send_stock_notifications
        from product.models import Variant
        active_variants = Variant.objects.filter(
            product__category=category,
            product__is_active=True,
            product__is_deleted=False,
            is_active=True,
            stock__gt=0,
        )
        for variant in active_variants:
            _send_stock_notifications(variant)

        if restored_products > 0:
            messages.success(
                request,
                f"'{category.name}' restored! {restored_products} product(s) are now live on the storefront again."
            )
        else:
            messages.success(
                request, f"'{category.name}' has been successfully restored."
            )
        return redirect("category_management")

    return redirect("category_management")


@never_cache
@admin_required
def permanent_delete_category(request, id):
    if request.method == "POST":
        category = get_object_or_404(Category, id=id)

        if not category.is_deleted:
            messages.error(
                request,
                "Please archive the category first before permanently deleting.",
            )
            return redirect("category_management")

        # Count products that will become uncategorized
        affected = category.products.filter(is_deleted=False).count()

        category.delete()  # permanent delete — products become category=NULL (uncategorized)

        if affected > 0:
            messages.warning(
                request,
                f"Category permanently deleted. {affected} product(s) are now uncategorized — "
                f"go to Product Management to reassign them."
            )
        else:
            messages.success(request, "Category permanently deleted.")
        return redirect("category_management")

    return redirect("category_management")


# Create your views here.
