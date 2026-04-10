from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
from email.mime.image import MIMEImage
import os

def send_back_in_stock_email(user, variant, request=None):
    """
    Sends a premium luxury-tier back-in-stock notification email.
    """
    # Pre-calculate product image and attach as CID
    primary = variant.product.images.filter(is_primary=True).first()
    if not primary:
        primary = variant.product.images.first()
    
    attached_images = []
    if primary and primary.image:
        image_path = primary.image.path
        if os.path.exists(image_path):
            cid_id = f"stock_img_{variant.id}"
            variant.cid_id = cid_id
            attached_images.append({
                'path': image_path,
                'cid': cid_id
            })
        else:
            variant.cid_id = None
    else:
        variant.cid_id = None

    context = {
        'user': user,
        'variant': variant,
        'request': request,
    }

    html_content = render_to_string('wishlist/email/back_in_stock.html', context)
    text_content = strip_tags(html_content)
    
    subject = f"Your Favorite Item is Back in Stock! - {variant.product.name} 🎉"
    from_email = settings.EMAIL_HOST_USER
    to_email = [user.email]
    
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
