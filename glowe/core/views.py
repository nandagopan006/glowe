from django.shortcuts import render,redirect
from django.contrib.auth import authenticate,logout
from product.models import Product, Category
from django.db.models import Q, Count, Avg
from order.models import OrderItem

# Create your views here.
def home(request):
    
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_dashboard')
    
    welcome = request.session.pop('welcome', None)
    
    # Get featured/new products (latest 8 products)
    featured_products = Product.objects.filter(
        is_deleted=False,
        is_active=True
    ).prefetch_related('images', 'variants').order_by('-created_at')[:8]
    
    # Get best selling products (top 4 by order count)
    best_sellers = Product.objects.filter(
        is_deleted=False,
        is_active=True
    ).annotate(
        order_count=Count('variants__orderitem')
    ).filter(order_count__gt=0).order_by('-order_count')[:4]
    
    # Get all active categories
    categories = Category.objects.filter(
        is_deleted=False
    ).order_by('name')[:6]
    
    context = {
        'welcome': welcome,
        'featured_products': featured_products,
        'best_sellers': best_sellers,
        'categories': categories,
    }
    
    return render(request, 'home.html', context)

def signout(request):
    logout(request)
    return redirect('signin')