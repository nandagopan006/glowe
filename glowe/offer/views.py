from django.shortcuts import render, get_object_or_404
from decimal import Decimal
from datetime import datetime
from django.utils import timezone

from .models import Offer, OfferItem
from .forms import OfferForm
from product.models import Product
from category.models import Category
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from core.decorators import admin_required


@never_cache
@admin_required
def add_offer(request):

    products = Product.objects.all()
    categories = Category.objects.all()

    if request.method == "POST":
        form = OfferForm(request.POST)
        
        if form.is_valid():
            offer = form.save()
            apply_to = form.cleaned_data.get("apply_to")
            product_id = form.cleaned_data.get("product_id")
            category_id = form.cleaned_data.get("category_id")

            if apply_to == "PRODUCT":
                OfferItem.objects.create(
                    offer=offer, apply_to="PRODUCT", product_id=product_id
                )
            else:
                OfferItem.objects.create(
                    offer=offer, apply_to="CATEGORY", category_id=category_id
                )

            return JsonResponse(
                {"success": True, "message": "Offer created successfully"}
            )
        else:
            errors = {}
            for field, error_list in form.errors.items():
                if field == '__all__':
                    errors['non_field_errors'] = [str(e) for e in error_list]
                else:
                    errors[field] = [str(e) for e in error_list]
            return JsonResponse({"success": False, "errors": errors})

    return render(
        request,
        "admin/offer_list.html",
        {"products": products, "categories": categories},
    )


@never_cache
@admin_required
def edit_offer(request, id):

    offer = get_object_or_404(Offer, id=id)
    item = OfferItem.objects.get(offer=offer)

    if request.method == "POST":
        form = OfferForm(request.POST, instance=offer)
        
        if form.is_valid():
            form.save()
            return JsonResponse(
                {"success": True, "message": "Offer updated successfully"}
            )
        else:
            errors = {}
            for field, error_list in form.errors.items():
                if field == '__all__':
                    errors['non_field_errors'] = [str(e) for e in error_list]
                else:
                    errors[field] = [str(e) for e in error_list]
            return JsonResponse({"success": False, "errors": errors})

    return render(
        request, "admin/offer_list.html", {"offer": offer, "item": item}
    )


@never_cache
@admin_required
def offer_list(request):

    offers = Offer.objects.all().order_by("-created_at")
    products = Product.objects.all()
    categories = Category.objects.all()

    search = request.GET.get("search")
    offer_type = request.GET.get("type")
    status = request.GET.get("status")

    now = timezone.now()

    if search:
        offers = offers.filter(name__icontains=search)

    # type
    if offer_type == "PRODUCT":
        offers = offers.filter(items__apply_to="PRODUCT")

    elif offer_type == "CATEGORY":
        offers = offers.filter(items__apply_to="CATEGORY")

    # filter by status
    if status == "ACTIVE":
        offers = offers.filter(
            is_active=True, start_date__lte=now, end_date__gte=now
        )

    elif status == "SCHEDULED":
        offers = offers.filter(start_date__gt=now)

    elif status == "EXPIRED":
        offers = offers.filter(end_date__lt=now)

    offer_data = []

    for offer in offers:
        item = OfferItem.objects.filter(offer=offer).first()

        # STATUS LOGIC
        if not offer.is_active:
            offer_status = "Inactive"
        elif offer.start_date > now:
            offer_status = "Scheduled"
        elif offer.end_date < now:
            offer_status = "Expired"
        else:
            offer_status = "Active"

        offer_data.append(
            {"offer": offer, "item": item, "status": offer_status}
        )

    paginator = Paginator(offer_data, 5)
    page = request.GET.get("page")
    offers = paginator.get_page(page)

    return render(
        request,
        "admin/offer_list.html",
        {
            "offers": offers,
            "products": products,
            "categories": categories,
        },
    )


@never_cache
@admin_required
def toggle_offer(request, id):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid request"})

    offer = get_object_or_404(Offer, id=id)
    now = timezone.now()

    if offer.end_date < now and not offer.is_active:
        return JsonResponse(
            {"success": False, "error": "Cannot activate expired offer"}
        )

    offer.is_active = not offer.is_active
    offer.save()

    return JsonResponse(
        {
            "success": True,
            "message": f"Offer {'activated' if offer.is_active else 'deactivated'} successfully",  # noqa: E501
            "is_active": offer.is_active,
        }
    )


@never_cache
@admin_required
def delete_offer(request, id):
    if request.method == "POST":
        offer = get_object_or_404(Offer, id=id)
        offer.delete()
        return JsonResponse(
            {"success": True, "message": "Offer deleted successfully"}
        )

    return JsonResponse({"success": False, "error": "Invalid request"})
