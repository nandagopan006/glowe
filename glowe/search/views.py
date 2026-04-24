from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Q
from product.models import Product,ProductImage,Variant


def search_view(request):
    query = request.GET.get('q', '').strip()
    results = []

    if query:
        products = Product.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query),
            is_active=True,
            is_deleted=False
        ).prefetch_related('images', 'variants').distinct()

        for product in products:
            primary_image = product.images.filter(is_primary=True).first() or product.images.first()
            default_variant = product.variants.filter(is_default=True, is_active=True).first() or product.variants.filter(is_active=True).first()
            results.append({
                'product': product,
                'image': primary_image,
                'variant': default_variant,
            })

    return render(request, 'search/search.html', {
        'query': query,
        'results': results,
        'result_count': len(results),
    })


def search_suggestions(request):
    query = request.GET.get('q', '').strip()
    data = []

    if query and len(query) >= 2:
        products = Product.objects.filter(
            name__icontains=query,
            is_active=True,
            is_deleted=False
        ).prefetch_related('images', 'variants')[:5]

        for product in products:
            primary_image = product.images.filter(is_primary=True).first() or product.images.first()
            default_variant = product.variants.filter(is_default=True, is_active=True).first() or product.variants.filter(is_active=True).first()

            data.append({
                'id': product.id,
                'name': product.name,
                'slug': product.slug,
                'price': str(default_variant.price) if default_variant else None,
                'image': primary_image.image.url if primary_image else None,
            })

    return JsonResponse({'results': data})
