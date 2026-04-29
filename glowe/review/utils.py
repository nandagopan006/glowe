
from .models import Review


def can_user_review(user,product,order):
    if order.user !=user :
        return False
    
    if order.status!= 'DELVERED':
        return False
    
    if not order.items.filter(product=product).exists():
        return False

    if Review.objects.filter(user=user, product=product, order=order).exists():
        return False

    return True