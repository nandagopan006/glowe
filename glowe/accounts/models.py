from django.db import models
from django.contrib.auth.models import AbstractUser
import random
import string
from django.db.models.signals import post_save
from django.dispatch import receiver


class ProfileUser(AbstractUser):
    full_name = models.CharField(max_length=60)
    email = models.EmailField(max_length=60)
    phone_number = models.CharField(
        max_length=15, unique=True, null=True, blank=True
    )
    profile_image = models.ImageField(
        upload_to="profile/",
        default="profile/default.png",
        null=True,
        blank=True,
    )

    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Referral logic (Kept in main model as requested)
    referral_code = models.CharField(max_length=10, blank=True, null=True)
    referred_by = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True
    )
    referral_count = models.IntegerField(default=0)

    def save(self, *args, **kwargs):
        if not self.referral_code:
            while True:
                code = "".join(
                    random.choices(string.ascii_uppercase + string.digits, k=8)
                )
                if not ProfileUser.objects.filter(referral_code=code).exists():
                    self.referral_code = code
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email

    class Meta:
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["created_at"]),
        ]


class UserSecurity(models.Model):
    user = models.OneToOneField(
        ProfileUser, on_delete=models.CASCADE, related_name="security"
    )
    # OTP tracking
    resend_count = models.IntegerField(default=0)
    resend_blocked_until = models.DateTimeField(null=True, blank=True)

    # Password reset tracking
    reset_token = models.CharField(max_length=255, null=True, blank=True)
    reset_requested_at = models.DateTimeField(null=True, blank=True)
    reset_block_until = models.DateTimeField(null=True, blank=True)
    reset_attempts = models.IntegerField(default=0)

    class Meta:
        verbose_name_plural = "User Security"


class OTPVerification(models.Model):
    user = models.ForeignKey(
        ProfileUser, on_delete=models.CASCADE, related_name="otps"
    )

    otp_code = models.CharField(max_length=4)
    expires_at = models.DateTimeField()
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class LoginAttempt(models.Model):
    ip_address = models.GenericIPAddressField()
    username = models.EmailField(max_length=255, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_successful = models.BooleanField(default=False)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["ip_address", "timestamp"]),
        ]

    def __str__(self):
        status = "Success" if self.is_successful else "Failed"
        return f"{status} login from {self.ip_address} for {self.username} at {self.timestamp}"


@receiver(post_save, sender=ProfileUser)
def create_user_profiles(sender, instance, created, **kwargs):
    if created:
        UserSecurity.objects.create(user=instance)


@receiver(post_save, sender=ProfileUser)
def save_user_profiles(sender, instance, **kwargs):
    # Check if security exists before saving
    if hasattr(instance, "security"):
        instance.security.save()
