from django.db import models
from django.contrib.auth.models import AbstractUser


class ProfileUser(AbstractUser):
    full_name=models.CharField(max_length=150)
    phone_number=models.CharField(max_length=15,unique=True,null=True,blank=True)
    profile_image=models.ImageField(upload_to='profile/',
                                    default='profile/default.png'
                                    ,null=True,blank=True)
    
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    resend_count = models.IntegerField(default=0)
    resend_blocked_until = models.DateTimeField(null=True, blank=True)
       
    # Password reset fields 
    reset_token= models.CharField(max_length=255, null=True, blank=True)   # stores latest valid token
    reset_requested_at= models.DateTimeField(null=True, blank=True)   # when re
    reset_block_until= models.DateTimeField(null=True, blank=True)  #set was requested
    reset_attempts = models.IntegerField(default=0)            # resend attempt count block end time


class OTPVerification(models.Model):
    user = models.ForeignKey(
        ProfileUser,
        on_delete=models.CASCADE,
        related_name='otps')
 
    otp_code=models.CharField(max_length=4)           
    expires_at=models.DateTimeField()                  
    is_verified= models.BooleanField(default=False)     
    created_at= models.DateTimeField(auto_now_add=True)  
 
    class Meta:
        ordering = ['-created_at']
