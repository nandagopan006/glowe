from .models import Cart

def get_user_cart(user):
    cart, created = Cart.objects.get_or_create(user=user)
    return cart 