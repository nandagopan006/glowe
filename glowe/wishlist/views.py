from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import Wishlist
from product.models import Variant


def add_to_wishlist(request, variant_id):
    variant = get_object_or_404(Variant, id=variant_id, is_active=True)

    if Wishlist.objects.filter(user=request.user, variant=variant).exist():
        messages.warning(request, "Already in wishlist")

    else:
        Wishlist.objects.create(user=request.user, variant=variant)
        messages.success(request, "Added to wishlist")

    wishlist_items = Wishlist.objects.filter(user=request.user).select_related(
        "variant", "variant__product"
    )

    return render(request, "wishlist/wishlist.html",{"wishlist_items": wishlist_items})

def wishlist_page(request):
    return render(request, "wishlist/wishlist.html")