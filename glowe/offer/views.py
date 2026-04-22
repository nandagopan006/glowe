from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from decimal import Decimal, InvalidOperation
from datetime import datetime
from django.utils import timezone

from .models import Offer, OfferItem
from product.models import Product
from category.models import Category
from django.core.paginator import Paginator
from django.http import JsonResponse

def add_offer(request):

    products = Product.objects.all()
    categories = Category.objects.all()

    if request.method == "POST":

        name = request.POST.get("name")
        discount_type = request.POST.get("discount_type")
        discount_value = request.POST.get("discount_value")
        max_discount = request.POST.get("max_discount")
        min_purchase = request.POST.get("min_purchase")

        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")

        apply_to = request.POST.get("apply_to")
        product_id = request.POST.get("product_id")
        category_id = request.POST.get("category_id")

        # error return (changed)
        def error(msg):
            return JsonResponse({"success": False, "error": msg})

        # validation (same)
        if not name:
            return error("Offer name required")

        try:
            discount_value = Decimal(discount_value)
        except (InvalidOperation, TypeError):
            return error("Invalid discount value")

        if discount_value <= 0:
            return error("Discount must be greater than 0")

        if discount_type not in ["PERCENTAGE", "FLAT"]:
            return error("Invalid discount type")

        if discount_type == "PERCENTAGE" and discount_value > 100:
            return error("Percentage cannot exceed 100")

        if max_discount:
            try:
                max_discount = Decimal(max_discount)
                if max_discount <= 0:
                    return error("Max discount must be > 0")
            except:
                return error("Invalid max discount")

        if min_purchase:
            try:
                min_purchase = Decimal(min_purchase)
                if min_purchase <= 0:
                    return error("Min purchase must be > 0")
            except:
                return error("Invalid min purchase")

        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
            end_date = datetime.strptime(end_date, "%Y-%m-%d")
        except:
            return error("Invalid date format")

        if start_date >= end_date:
            return error("End date must be after start date")

        if apply_to == "PRODUCT" and not product_id:
            return error("Select a product")

        if apply_to == "CATEGORY" and not category_id:
            return error("Select a category")

        now = timezone.now()

        if apply_to == "PRODUCT":
            exists = OfferItem.objects.filter(
                product_id=product_id,
                apply_to="PRODUCT",
                offer__is_active=True,
                offer__start_date__lte=now,
                offer__end_date__gte=now
            ).exists()

            if exists:
                return error("This product already has an active offer")

        if apply_to == "CATEGORY":
            exists = OfferItem.objects.filter(
                category_id=category_id,
                apply_to="CATEGORY",
                offer__is_active=True,
                offer__start_date__lte=now,
                offer__end_date__gte=now
            ).exists()

            if exists:
                return error("This category already has an active offer")

        # save (same)
        offer = Offer.objects.create(
            name=name,
            discount_type=discount_type,
            discount_value=discount_value,
            max_discount=max_discount if discount_type == "PERCENTAGE" else None,
            min_purchase=min_purchase,
            start_date=start_date,
            end_date=end_date,
            is_active=True
        )

        if apply_to == "PRODUCT":
            OfferItem.objects.create(offer=offer, apply_to="PRODUCT", product_id=product_id)
        else:
            OfferItem.objects.create(offer=offer, apply_to="CATEGORY", category_id=category_id)

        return JsonResponse({"success": True, "message": "Offer created successfully"})

    return render(request, "admin/offer_list.html", {
        "products": products,
        "categories": categories
    })


def edit_offer(request, id):

    offer = get_object_or_404(Offer, id=id)
    item = OfferItem.objects.get(offer=offer)

    if request.method == "POST":

        name = request.POST.get("name")
        discount_value = request.POST.get("discount_value")
        max_discount = request.POST.get("max_discount")
        min_purchase = request.POST.get("min_purchase")
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")

        # error return
        def error(msg):
            return JsonResponse({"success": False, "error": msg})

        # validation 
        if not name:
            return error("Offer name required")

        try:
            discount_value = Decimal(discount_value)
        except (InvalidOperation, TypeError):
            return error("Invalid discount value")

        if discount_value <= 0:
            return error("Discount must be greater than 0")

        if offer.discount_type == "PERCENTAGE" and discount_value > 100:
            return error("Percentage cannot exceed 100")

        if max_discount:
            try:
                max_discount = Decimal(max_discount)
                if max_discount <= 0:
                    return error("Max discount must be > 0")
            except:
                return error("Invalid max discount")

        if min_purchase:
            try:
                min_purchase = Decimal(min_purchase)
                if min_purchase <= 0:
                    return error("Min purchase must be > 0")
            except:
                return error("Invalid min purchase")

        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
            end_date = datetime.strptime(end_date, "%Y-%m-%d")
        except:
            return error("Invalid date format")

        if start_date >= end_date:
            return error("End date must be after start date")

        # save (same)
        offer.name = name
        offer.discount_value = discount_value
        offer.max_discount = max_discount if offer.discount_type == "PERCENTAGE" else None
        offer.min_purchase = min_purchase
        offer.start_date = start_date
        offer.end_date = end_date

        offer.save()

        return JsonResponse({"success": True, "message": "Offer updated successfully"})

    return render(request, "admin/offer_list.html", {
        "offer": offer,
        "item": item
    })

def offer_list(request):

    offers = Offer.objects.all().order_by("-created_at")

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
        offers=offers.filter(items__apply_to="CATEGORY")

    # filter by status
    if status == "ACTIVE":
        offers=offers.filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        )

    elif status == "SCHEDULED":
        offers=offers.filter(start_date__gt=now)

    elif status == "EXPIRED":
        offers =offers.filter(end_date__lt=now)

    
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

        offer_data.append({
            "offer": offer,
            "item": item,
            "status": offer_status
        })
        
    paginator = Paginator(offer_data, 5)
    page = request.GET.get("page")
    offers = paginator.get_page(page)

    return render(request, "admin/offer_list.html", {
        "offers": offer_data,
    })


def toggle_offer(request, id):

    if request.method != "POST":
        messages.error(request, "Invalid request")
        return redirect("offer_list")

    offer = get_object_or_404(Offer, id=id)

    now = timezone.now()

    #Prevent activating expired offers
    if offer.end_date < now:
        messages.error(request, "Cannot activate expired offer")
        return redirect("offer_list")

    #Toggle
    offer.is_active = not offer.is_active
    offer.save()

    if offer.is_active:
        messages.success(request, "Offer activated")
    else:
        messages.success(request, "Offer deactivated")

    return redirect("offer_list")

def delete_offer(request, id):

    if request.method == "POST":

        offer = get_object_or_404(Offer, id=id)

        offer.delete()

        return JsonResponse({
            "success": True,
            "message": "Offer deleted successfully"
        })

    return JsonResponse({
        "success": False,
        "error": "Invalid request"
    })
    
