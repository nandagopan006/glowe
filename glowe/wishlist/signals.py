
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings

from product.models import Variant
from .models import StockNotification
from .email_util import send_back_in_stock_email

@receiver(post_save,sender=Variant)
def notify_user_when_in_stock(sender,instance,**kwargs) :
    if instance.stock > 0:
        
        notifications = StockNotification.objects.filter(
            variant=instance,is_notified=False
        )
        for n in notifications:
            user = n.user
            
            # Send premium back-in-stock email
            send_back_in_stock_email(user, instance)
            
            # Mark as notified to prevent duplicate emails
            n.is_notified = True
            n.save()