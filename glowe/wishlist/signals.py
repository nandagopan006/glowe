
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings

from product.models import Variant
from .models import StockNotification

@receiver(post_save,sender=Variant)
def notify_user_when_in_stock(sender,instance,**kwargs) :
    if instance.stock > 0:
        
        notifications = StockNotification.objects.filter(
            variant=instance,is_notified=False
        )
        for n in notifications:
            user = n.user
            
            subject = "Your Wishlist Item is Back in Stock! 🎉"

            message = (
                f"Hi {user.full_name},\n\n"
                f"Good news! The product \"{instance.product.name}\" is now back in stock.\n\n"
                f"You can now add it to your cart and purchase it.\n\n"
                f"Visit the website and grab it before it runs out again!\n\n"
                f"Thank you for Visiting with us.\n"
            )

            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER,
                [user.email],
                fail_silently=False,
            )
            
            # Mark as notified to prevent duplicate emails
            n.is_notified = True
            n.save()