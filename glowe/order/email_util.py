from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
from email.mime.image import MIMEImage
import os

def send_order_confirmation_email(request, order):
   
    order_items = order.items.select_related('variant', 'variant__product').prefetch_related('variant__product__images')
    
   
    attached_images = []
    for i, item in enumerate(order_items):
        primary = item.variant.product.images.filter(is_primary=True).first()
        if not primary:
            primary = item.variant.product.images.first()
        
        if primary and primary.image:
            image_path = primary.image.path
            if os.path.exists(image_path):
                cid_id = f"prod_img_{i}"
                item.cid_id = cid_id
                attached_images.append({
                    'path': image_path,
                    'cid': cid_id
                })
            else:
                item.cid_id = None
        else:
            item.cid_id = None

    context = {
        'order': order,
        'order_items': order_items,
        'request': request,
    }
    
    # Render the HTML template
    html_content = render_to_string('order/email/order_confirmation.html', context)
    
    # Create the text version (for email clients that don't support HTML)
    text_content = strip_tags(html_content)
    
    # Create the email object
    subject = f'Order Confirmation - {order.order_number} 🛍️'
    from_email = settings.EMAIL_HOST_USER
    to_email = [order.user.email]
    
    email = EmailMultiAlternatives(
        subject,
        text_content,
        from_email,
        to_email
    )
    email.attach_alternative(html_content, "text/html")
    
    # Attach product images as CIDs
    for img_data in attached_images:
        try:
            with open(img_data['path'], 'rb') as f:
                img = MIMEImage(f.read())
                img.add_header('Content-ID', f"<{img_data['cid']}>")
                img.add_header('Content-Disposition', 'inline')
                email.attach(img)
        except Exception:
            pass

    # Send the email
    email.send(fail_silently=False)

def send_order_cancellation_email(request, order, cancelled_items=None, is_full_cancel=False, refund_amount=0):
    """
    Sends a professional luxury-tier order/item cancellation email.
    """
    if is_full_cancel:
        # Show all items if full order is cancelled
        items_to_show = order.items.select_related('variant', 'variant__product').prefetch_related('variant__product__images')
    else:
        # Show only specifically cancelled items
        items_to_show = cancelled_items

    # Pre-calculate images and attach as CIDs
    attached_images = []
    for i, item in enumerate(items_to_show):
        primary = item.variant.product.images.filter(is_primary=True).first()
        if not primary:
            primary = item.variant.product.images.first()
        
        if primary and primary.image:
            image_path = primary.image.path
            if os.path.exists(image_path):
                cid_id = f"cancel_img_{i}"
                item.cid_id = cid_id
                attached_images.append({
                    'path': image_path,
                    'cid': cid_id
                })
            else:
                item.cid_id = None
        else:
            item.cid_id = None

    context = {
        'order': order,
        'items_to_show': items_to_show,
        'is_full_cancel': is_full_cancel,
        'refund_amount': refund_amount,
        'request': request,
    }

    html_content = render_to_string('order/email/order_cancellation.html', context)
    text_content = strip_tags(html_content)
    
    subject = f"{'Order' if is_full_cancel else 'Item'} Cancelled - {order.order_number} ❌"
    from_email = settings.EMAIL_HOST_USER
    to_email = [order.user.email]
    
    email = EmailMultiAlternatives(subject, text_content, from_email, to_email)
    email.attach_alternative(html_content, "text/html")
    
    for img_data in attached_images:
        try:
            with open(img_data['path'], 'rb') as f:
                img = MIMEImage(f.read())
                img.add_header('Content-ID', f"<{img_data['cid']}>")
                img.add_header('Content-Disposition', 'inline')
                email.attach(img)
        except Exception:
            pass

    email.send(fail_silently=False)

def send_order_delivered_email(request, order):
    """
    Sends a premium luxury-tier order delivered email (Everlane Style).
    """
    order_items = order.items.select_related('variant', 'variant__product').prefetch_related('variant__product__images')
    
    # Pre-calculate images and attach as CIDs
    attached_images = []
    for i, item in enumerate(order_items):
        primary = item.variant.product.images.filter(is_primary=True).first()
        if not primary:
            primary = item.variant.product.images.first()
        
        if primary and primary.image:
            image_path = primary.image.path
            if os.path.exists(image_path):
                cid_id = f"dev_img_{i}"
                item.cid_id = cid_id
                attached_images.append({
                    'path': image_path,
                    'cid': cid_id
                })
            else:
                item.cid_id = None
        else:
            item.cid_id = None

    context = {
        'order': order,
        'order_items': order_items,
        'request': request,
    }

    html_content = render_to_string('order/email/order_delivered.html', context)
    text_content = strip_tags(html_content)
    
    subject = f"Your Glowé Order Has Been Delivered - {order.order_number} 🎉"
    from_email = settings.EMAIL_HOST_USER
    to_email = [order.user.email]
    
    email = EmailMultiAlternatives(subject, text_content, from_email, to_email)
    email.attach_alternative(html_content, "text/html")
    
    for img_data in attached_images:
        try:
            with open(img_data['path'], 'rb') as f:
                img = MIMEImage(f.read())
                img.add_header('Content-ID', f"<{img_data['cid']}>")
                img.add_header('Content-Disposition', 'inline')
                email.attach(img)
        except Exception:
            pass

    email.send(fail_silently=False)
