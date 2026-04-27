from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from accounts.models import ProfileUser
from wallet.models import Wallet

class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        # This is called before the social login is completed.
        pass

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        
        # Populate full_name from social data if it exists
        if not user.full_name:
            first_name = sociallogin.account.extra_data.get('given_name', '')
            last_name = sociallogin.account.extra_data.get('family_name', '')
            user.full_name = f"{first_name} {last_name}".strip()
            if not user.full_name:
                user.full_name = user.email.split('@')[0]
        
        user.is_verified = True
        user.is_active = True
        user.save()
        
        # Ensure wallet exists
        Wallet.objects.get_or_create(user=user)
        
        return user
