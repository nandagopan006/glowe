from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from accounts.models import ProfileUser, OTPVerification
from .models import Address
from .forms import AddressForm
from allauth.socialaccount.models import SocialAccount
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import update_session_auth_hash
import random
import re
import os



@login_required
def profile_overview(request):
    user=request.user
    social_account=SocialAccount.objects.filter(user=user).first()
    success=request.session.pop('success',None)

    context={
        "user":user,
        "social_account":social_account,
        "success": success,
    }
    return render(request,'profile_overview.html', context,)

@login_required
def edit_profile(request):
    user=request.user
    social_account=SocialAccount.objects.filter(user=user).first()

   
    if social_account:
        print("SOCIAL DATA:",social_account.extra_data)

    
    if social_account:
        google_email =social_account.extra_data.get('email')
        if google_email and user.email !=google_email:
            user.email=google_email
            user.save()

    if request.method=='POST':

        full_name=request.POST.get('full_name', '').strip()
        email=request.POST.get('email', '').strip().lower()
        phone_number=request.POST.get('phone_number', '').strip()

        
        if not email and social_account:
            email=social_account.extra_data.get('email', '').lower()

      
        if not full_name:
            messages.error(request,'Full name is required')
            return redirect('edit_profile')

        if len(full_name) < 4:
            messages.error(request,'Full name must be at least 4 characters')
            return redirect('edit_profile')

        if '  ' in full_name:
            messages.error(request,'Double spaces not allowed')
            return redirect('edit_profile')

        if not full_name.replace(' ', '').isalpha():
            messages.error(request, 'Only letters allowed in name')
            return redirect('edit_profile')

        
        if not email:
            messages.error(request, 'Email not found. Please login again.')
            return redirect('edit_profile')

        email_pattern =r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        if not re.match(email_pattern, email):
            messages.error(request, 'Enter valid email')
            return redirect('edit_profile')

        
        if phone_number:
            clean_phone =phone_number.replace(' ', '')

            phone_pattern =r'^(\+91)?[6-9]\d{9}$'
            if not re.match(phone_pattern, clean_phone):
                messages.error(request, 'Invalid Indian phone number')
                return redirect('edit_profile')

            if ProfileUser.objects.filter(phone_number=clean_phone).exclude(pk=user.pk).exists():
                messages.error(request, 'Phone already used')
                return redirect('edit_profile')
        else:
            clean_phone=None

        changed=False

 
        if full_name!=user.full_name:
            user.full_name=full_name
            changed=True

        if clean_phone!=user.phone_number:
            user.phone_number=clean_phone
            changed=True

        
        if email!=user.email:

            if social_account:
                messages.error(request, 'Google users cannot change email')
                return redirect('edit_profile')

            if ProfileUser.objects.filter(email=email, is_verified=True).exclude(pk=user.pk).exists():
                messages.error(request, 'Email already used')
                return redirect('edit_profile')

            if changed:
                user.save()

            otp_code=str(random.randint(1000, 9999))

            OTPVerification.objects.filter(user=user, is_verified=False).delete()

            OTPVerification.objects.create(
                user=user,
                otp_code=otp_code,
                expires_at=timezone.now()+timedelta(minutes=5)
            )

            request.session['new_email']=email

            send_mail(
                'Verify your new email',
                f'Your OTP is {otp_code}. Valid for 5 minutes.',
                settings.EMAIL_HOST_USER,
                [email],
            )

            messages.success(request, f'OTP sent to {email}')
            return redirect('verify_email_change', extra_tags='show_on_overview')

        if changed:
            user.save()
            request.session["success"]='Profile updated successfully'
        return redirect('profile_overview')

    return render(request,'edit_profile.html', {
        "user": user,
        "social_account":social_account,
    })


@login_required
def verify_email_change(request):
    user =request.user
    new_email =request.session.get('new_email')

    if not new_email:
        return redirect('edit_profile')

    otp_record =OTPVerification.objects.filter(user=user, is_verified=False).first()

    if not otp_record:
        messages.error(request, 'OTP expired')
        return redirect('edit_profile')

    seconds_left =max(0, int((otp_record.expires_at -timezone.now()).total_seconds()))

    if request.method =='POST':

        # RESEND
        if request.POST.get('action') =='resend':
            OTPVerification.objects.filter(user=user,is_verified=False).delete()

            otp_code = str(random.randint(1000, 9999))

            OTPVerification.objects.create(
                user=user,
                otp_code=otp_code,
                expires_at=timezone.now() +timedelta(minutes=5)
            )

            send_mail(
                'Resend OTP',
                f'Your new OTP is {otp_code}',
                settings.EMAIL_HOST_USER,
                [new_email],
            )

            messages.success(request, 'OTP resent')
            return redirect('verify_email_change')

        
        entered_otp = request.POST.get('otp', '').strip()

        if timezone.now() > otp_record.expires_at:
            messages.error(request, 'OTP expired')
            return redirect('verify_email_change')

        if otp_record.otp_code != entered_otp:
            messages.error(request, 'Invalid OTP')
            return redirect('verify_email_change')

        otp_record.is_verified=True
        otp_record.save()

        user.email=new_email
        user.username =new_email
        user.save()

        request.session.pop('new_email',None)

        messages.success(request,'Email updated successfully')
        return redirect('profile_overview')

    return render(request,'verify_email_change.html', {
        'pending_email':new_email,
        'seconds_left':seconds_left,
    })



@login_required
def cancel_email_verification(request):
    request.session.pop('new_email', None)
    OTPVerification.objects.filter(user=request.user, is_verified=False).delete()

    messages.error(request,'Email change cancelled')
    return redirect('edit_profile')



@login_required
def add_profile_image(request):
    if request.method =="POST":
        user=request.user
        image=request.FILES.get('profile_image')

        if not image:
            messages.error(request,'Select an image')
            return redirect('edit_profile')

        if image.content_type not in ['image/jpeg', 'image/png','image/jpg', 'image/webp']:
            messages.error(request,'Only JPG, PNG, WEBP allowed')
            return redirect('edit_profile')

        # delete old image
        if user.profile_image and user.profile_image.name !='profile/default.png':
            if os.path.exists(user.profile_image.path):
                os.remove(user.profile_image.path)

        user.profile_image =image
        user.save()

        messages.success(request, 'Profile image updated')
        return redirect('edit_profile')

    return redirect('edit_profile')



@login_required
def remove_profile_image(request):
    user =request.user

    if user.profile_image and user.profile_image.name!='profile/default.png':
        if os.path.exists(user.profile_image.path):
            os.remove(user.profile_image.path)

        user.profile_image='profile/default.png'
        user.save()

        messages.success(request,'Profile image removed')
    else:
        messages.error(request,'No image to remove')

    return redirect('edit_profile')



@login_required
def change_password(request):
    user=request.user

    if request.method=="POST":
        current_password=request.POST.get('current_password')
        new_password=request.POST.get('new_password')
        confirm_password=request.POST.get('confirm_password')

        if not user.check_password(current_password):
            messages.error(request,"Current password is incorrect")
            return redirect('change_password')

        password_pattern=r'^(?=.*[A-Z])(?=.*[0-9])(?=.*[!@#$%^&*(),.?":{}|<>]).{8,}$'
        if not re.match(password_pattern,new_password):
            messages.error(request,"Password must be at least 8 characters long, include one uppercase letter, one number and one special character")
            return redirect('change_password')

        if new_password !=confirm_password:
            messages.error(request,"Passwords do not match")
            return redirect('change_password')
        if user.check_password(new_password):
            messages.error(request,"New password cannot be same as old password")
            return redirect('change_password')

        
        user.set_password(new_password)
        user.save()
        
        #keep wih pass in logged
        update_session_auth_hash(request, user)
        
        send_mail(
    'Your Glowé Password Was Changed 🔐',
    f'''
════════════════════════════════
           🌿 Glowé
     Your Natural Beauty Store
════════════════════════════════

Hey {user.full_name or user.email.split('@')[0].capitalize()},

Your Glowé account password has been
successfully updated. ✅

  ──────────────────────────
  Account: {user.email}
  Changed: {timezone.now().strftime("%d %b %Y, %I:%M %p")} UTC
  ──────────────────────────

🔒 SECURITY NOTICE:
   If you made this change, you can
   safely ignore this email.

   If you did NOT make this change,
   your account may be compromised!
   Please contact us immediately at:
   📧 glowe639@gmail.com

   We recommend you:
   ✔ Change your password immediately
   ✔ Enable two-factor authentication
   ✔ Check your recent account activity

────────────────────────────────
💚 Why Glowé?
   ✔ 100% Natural Ingredients
   ✔ Dermatologist Tested
   ✔ Premium Luxury Skincare
   ✔ Cruelty Free
────────────────────────────────

Need help? Contact us:
📧 glowe639@gmail.com

════════════════════════════════
Thank you for choosing Glowé —
your natural beauty destination.

© 2025 Glowé. All rights reserved.
Kerala, India
════════════════════════════════
''',
    settings.EMAIL_HOST_USER,
    [user.email],
)
        messages.success(request,"Password updated successfully", extra_tags='show_on_overview')
        return redirect("profile_overview")
        
    
        
    return render(request,'change_password.html')

@login_required
def address(request):
    addresses=Address.objects.filter(user=request.user)
    return render(request,'address.html',{'addresses':addresses})

@login_required
def add_address(request):
    
    if request.method =="POST":
        form=AddressForm(request.POST)

        if form.is_valid():
           
            address=form.save(commit=False)
            address.user = request.user
            
           
            address.street_address= address.street_address.strip()
            address.city=address.city.strip()
            address.state=address.state.strip()
            address.district=address.district.strip()
            # dulti not allow
            exists = Address.objects.filter(
                user=request.user,street_address__iexact=address.street_address,
                city__iexact=address.city,state__iexact=address.state,pincode=address.pincode).exists()

            if exists:
                messages.error(request, "Address already exists")
                return redirect("address")

            # if no addr so first will def
            if not Address.objects.filter(user=request.user).exists():
                address.is_default=True
            elif address.is_default: #if usr add new add and set def so per need to chnge
                Address.objects.filter(user=request.user).update(is_default=False)

            address.save()

            messages.success(request,"Address added successfully")
            
            # Follow 'next' parameter if present to remain in checkout context
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
                
            return redirect('address')

    else:
        form=AddressForm()
       

    return render(request,'add_address.html',{'form':form})


@login_required
def edit_address(request, id):
    address=get_object_or_404(Address, id=id, user=request.user)
    if request.method =="POST":
        form=AddressForm(request.POST, instance=address) 

        if form.is_valid():
            updated=form.save(commit=False)
            updated.street_address=updated.street_address.strip()
            updated.city=updated.city.strip()
            updated.state=updated.state.strip()
            updated.district=updated.district.strip()

            exists=Address.objects.filter(user=request.user,street_address__iexact=updated.street_address,
                city__iexact=updated.city,state__iexact=updated.state,pincode=updated.pincode
            ).exclude(id=id).exists()

            if exists:
                messages.error(request,"This address already exists")
                return redirect('address')
            
            if updated.is_default:
                Address.objects.filter(user=request.user).exclude(id=id).update(is_default=False)

            updated.save()

            messages.success(request, "Updated successfully")
            
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)

            return redirect('address')
            
        else:
            messages.error(request, "Please fix the errors  ")

    else:
        form = AddressForm(instance=address)

    return render(request, 'edit_address.html', {'form': form, 'address': address})

@login_required
def delete_address(request, id):

    address = get_object_or_404(Address, id=id, user=request.user)

    if address.is_default:
        #assign auto other
        other=Address.objects.filter(user=request.user).exclude(id=id).first()
        #if dlt dlt make def as other
        if other:
            other.is_default=True
            other.save()

    address.delete()
    messages.success(request, "Address deleted successfully")

    return redirect("address")

@login_required
def set_default_address(request, id):
    address=get_object_or_404(Address, id=id, user=request.user)
    Address.objects.filter(user=request.user).update(is_default=False)

    address.is_default=True
    address.save()

    messages.success(request, "Default address updated")
    next_url = request.GET.get('next')
    if next_url:
        return redirect(next_url)

    return redirect('address')