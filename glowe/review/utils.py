
from .models import Review


def can_user_review(user,product,order):
    if order.user != user :
        return False
    
    if order.order_status != 'DELIVERED':
        return False
    
    if not order.items.filter(variant__product=product).exists():
        return False

    if Review.objects.filter(user=user, product=product, order=order).exists():
        return False

    return True