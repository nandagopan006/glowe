# invoice_utils.py
# This file calculates all the invoice data for an order.
# It handles: active items, cancelled items, returned items, discounts, refunds.

from decimal import Decimal
from django.apps import apps


def calculate_invoice(order):
 
    # Get all items for this order
    all_items = order.items.select_related(
        'variant__product'
    ).prefetch_related('variant__product__images')

    #Separate items by their status
    active_items = []
    cancelled_items = []
    returned_items = []

    for item in all_items:
        if item.item_status == 'CANCELLED':
            cancelled_items.append(item)
        elif item.item_status in ('RETURNED', 'RETURN_REQUESTED'):
            returned_items.append(item)
        else:
            active_items.append(item)

    
    active_subtotal = Decimal('0.00')
    for item in active_items:
        item.line_total = item.price_at_time * item.quantity
        active_subtotal += item.line_total

   
    cancelled_subtotal = Decimal('0.00')
    for item in cancelled_items:
        item.line_total = item.price_at_time * item.quantity
        cancelled_subtotal += item.line_total

   
    returned_subtotal = Decimal('0.00')
    for item in returned_items:
        item.line_total = item.price_at_time * item.quantity
        returned_subtotal += item.line_total

    # Get discount and shipping from the order
    discount = order.discount_amount or Decimal('0.00')
    shipping = order.delivery_charge or Decimal('0.00')

    
    grand_total = active_subtotal + shipping - discount
    if grand_total < Decimal('0.00'):
        grand_total = Decimal('0.00')

   
    from wallet.models import WalletTransaction
    refund_transactions = WalletTransaction.objects.filter(
        order=order,
        transaction_type='REFUND',
        status='COMPLETED'
    )

    total_refunded = Decimal('0.00')
    for txn in refund_transactions:
        total_refunded += txn.amount

   
    payment = getattr(order, 'payment', None)
    if payment:
        if payment.payment_status == 'SUCCESS':
            if total_refunded > Decimal('0.00'):
                payment_label = 'PARTIALLY REFUNDED' if total_refunded < order.total_amount else 'REFUNDED'
            else:
                payment_label = 'PAID'
        elif payment.payment_status == 'FAILED':
            payment_label = 'FAILED'
        else:
            payment_label = 'PENDING'
    else:
        payment_label = 'UNKNOWN'

    #Return everything as a clean dictionary
    return {
        'active_items': active_items,
        'cancelled_items': cancelled_items,
        'returned_items': returned_items,
        'active_subtotal': active_subtotal,
        'cancelled_subtotal': cancelled_subtotal,
        'returned_subtotal': returned_subtotal,
        'discount': discount,
        'shipping': shipping,
        'grand_total': grand_total,
        'total_refunded': total_refunded,
        'payment': payment,
        'payment_label': payment_label,
        'has_active': len(active_items) > 0,
        'has_cancelled': len(cancelled_items) > 0,
        'has_returned': len(returned_items) > 0,
    }
