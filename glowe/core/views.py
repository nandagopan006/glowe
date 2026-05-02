from django.shortcuts import render, redirect
from django.contrib.auth import logout
from product.models import Product, Category
from django.db.models import Count

from django.views.decorators.cache import never_cache


# Create your views here.
def home(request):

    if request.user.is_authenticated and request.user.is_superuser:
        return redirect("admin_dashboard")

    welcome = request.session.pop("welcome", None)

    # Get featured/new products (latest 8 products)
    featured_products = (
        Product.objects.filter(is_deleted=False, is_active=True)
        .prefetch_related("images", "variants")
        .order_by("-created_at")[:8]
    )

    # Get best selling products (top 4 by order count)
    best_sellers = (
        Product.objects.filter(is_deleted=False, is_active=True)
        .annotate(order_count=Count("variants__orderitem"))
        .filter(order_count__gt=0)
        .order_by("-order_count")[:4]
    )

    # Get all active categories
    categories = Category.objects.filter(is_deleted=False).order_by("name")[:6]

    context = {
        "welcome": welcome,
        "featured_products": featured_products,
        "best_sellers": best_sellers,
        "categories": categories,
    }

    return render(request, "home.html", context)


@never_cache
def signout(request):
    logout(request)
    return redirect("home")


def contact_page(request):
    return render(request, "user/contact.html")


def custom_404(request, exception):
    # Admin-side URL patterns
    ADMIN_PREFIXES = (
        "/admin-panel/",
        "/admin-dashboard/",
        "/adminpanel/",
        "/user-management/",
        "/categories/",
        "/products/",
        "/admin-signout/",
        "/offers/",
    )

    # Check if this is an admin path
    is_admin_path = any(request.path.startswith(prefix) for prefix in ADMIN_PREFIXES)

    if is_admin_path:
        # If user is logged in as admin, show admin 404
        if request.user.is_authenticated and request.user.is_superuser:
            return render(request, "admin/404_admin.html", status=404)
        # If not logged in, redirect to admin login
        else:
            return redirect("admin_signin")

    # Regular user 404
    return render(request, "404.html", status=404)
