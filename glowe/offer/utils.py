from decimal import Decimal
from django.utils import timezone
from .models import OfferItem

def calculate_discount(price, offer):

    price = Decimal(price)

    # Percentage discount
    if offer.discount_type == "PERCENTAGE":
        discount = (price * offer.discount_value) / Decimal("100")

        # apply max limit
        if offer.max_discount:
            if discount > offer.max_discount:
                discount=offer.max_discount

    # Flat discount
    else:
        discount =offer.discount_value

    # prevent discount more than price
    if discount > price:
        discount =price

    #round to 2 decimal
    discount=discount.quantize(Decimal("0.01"))

    return discount

def get_best_offer(product, price):

    now =timezone.now()

    # Product offers
    product_offers = OfferItem.objects.filter(
        apply_to="PRODUCT",
        product=product,
        offer__is_active=True,
        offer__start_date__lte=now,
        offer__end_date__gte=now
    )

    # Category offers
    category_offers = OfferItem.objects.filter(
        apply_to="CATEGORY",
        category=product.category,
        offer__is_active=True,
        offer__start_date__lte=now,
        offer__end_date__gte=now
    )

    all_items = list(product_offers) + list(category_offers)

    best_discount=Decimal("0.00")
    best_offer = None

    for item in all_items:
        discount=calculate_discount(price, item.offer)

        if discount > best_discount:
            best_discount =discount
            best_offer = item.offer

    return best_offer,best_discount