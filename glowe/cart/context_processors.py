def cart_count(request):
    count = 0
    if request.user.is_authenticated:
        if hasattr(request.user, 'cart'):
            count = request.user.cart.items.count()
    return {'cart_count': count}
