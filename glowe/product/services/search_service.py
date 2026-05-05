from django.db.models import Q
from product.models import Product

class SearchService:
    """
    Service layer to handle product search logic and suggestions.
    This separates the complex business logic from the view layer.
    """

    @staticmethod
    def search_products(query):
        """
        Search for active products by name or description.
        Returns a QuerySet of products.
        """
        if not query:
            return Product.objects.none()
            
        return Product.objects.filter(
            (Q(name__icontains=query) | Q(description__icontains=query)),
            is_active=True,
            is_deleted=False,
        ).distinct()

    @staticmethod
    def get_suggestions(query, limit=5):
        """
        Get simple search suggestions by product name.
        Returns a QuerySet of products.
        """
        if not query or len(query) < 2:
            return Product.objects.none()
            
        return Product.objects.filter(
            name__icontains=query, 
            is_active=True, 
            is_deleted=False
        )[:limit]
