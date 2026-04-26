from .models import Cart
from decimal import Decimal
from offer.utils import get_best_offer

def get_user_cart(user):
    cart, created = Cart.objects.get_or_create(user=user)
    return cart 

def get_cart_total(user):
    cart = get_user_cart(user)
    cart_items = cart.items.select_related('variant', 'variant__product', 'variant__product__category')
    
    total = Decimal('0.00')
    for item in cart_items:
        variant = item.variant
        product = variant.product
        
        # Only include active products, active variants, and stock > 0
        if product.is_active and not product.is_deleted and variant.is_active and variant.stock > 0:
            # Quantity should not exceed stock
            quantity = min(item.quantity, variant.stock)
            
            # Apply offer logic - Normal way
            price = Decimal(str(variant.price))
            offer, discount = get_best_offer(product, price)
            
            if offer:
                if discount > price:
                    discount = price
                final_price = price - discount
                if final_price < Decimal("0.00"):
                    final_price = Decimal("0.00")
            else:
                final_price = price
            
            total += quantity * final_price
            
    return total.quantize(Decimal("0.01"))