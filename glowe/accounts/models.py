from django.db import models
from django.contrib.auth.models import AbstractUser


class ProfileUser(AbstractUser):
    full_name=models.CharField(max_length=150)
    phone_number=models.CharField(max_length=15,unique=True,null=True,blank=True)
    profile_image=models.ImageField(upload_to='profile/',
                                    default='profile/default.png'
                                    ,null=True,blank=True)
    
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    otp=models.CharField(max_length=4,null=True,blank=True)
    #otp create time
    otp_created_at =models.DateTimeField(null=True,blank=True)
        
    resend_count = models.IntegerField(default=0)
    resend_blocked_until = models.DateTimeField(null=True, blank=True)

