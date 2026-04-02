# views.py

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from accounts.models import OTPVerification, ProfileUser
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.utils import timezone
from datetime import timedelta
import random
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import  get_object_or_404
import re
from django.core.paginator import Paginator
from django.db.models import Q
@never_cache
def admin_signin(request):

    # Already logged in admin
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_dashboard')
    if request.user.is_authenticated:
        return redirect("home")
    
    if request.method=="POST":
        email = request.POST.get('email')
        password = request.POST.get('password')

        
        if not email :
            messages.error(request,"Email is required")
            return render(request, 'auth/admin_signin.html', {'submitted_email': email}) 
        if not password :
            messages.error(request,"password is required")
            return render(request, 'auth/admin_signin.html', {'submitted_email': email}) 
        
        
        user = authenticate(request, username=email, password=password)

        if user is None:
            messages.error(request,"Invalid email or password")
            return render(request, 'auth/admin_signin.html', {'submitted_email': email})

        #admin acces not normal usr
        if not user.is_superuser:
            messages.error(request,"Access denied.Admin only.")
            return render(request, 'auth/admin_signin.html', {'submitted_email': email}) 
        
        login(request, user)
        
        request.session['success']='Welcome to the Dashboard'
        return redirect('admin_dashboard')

    return render(request, 'auth/admin_signin.html', {'submitted_email': ''})

@never_cache
@login_required(login_url='/admin-signin/')
def admin_dashboard(request):
    success=request.session.pop('success',None)
    if not request.user.is_superuser:
        return redirect('admin_signin')

    return render(request, 'admin_dashboard.html',{"success":success})

def admin_signout(request):
    logout(request)
    return redirect('admin_signin')


def admin_forget_password(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_dashboard')
    if request.user.is_authenticated:
        return redirect("home")
    
    if request.method=="POST":
        email=request.POST.get('email')

        if not email:
            messages.error(request,"Email required")
            return render(request, 'auth/admin_forget_password.html', {'submitted_email': email})

        try:
            user = ProfileUser.objects.get(email=email)

            
            if not user.is_superuser:
                messages.error(request,"Not authorized")
                return render(request, 'auth/admin_forget_password.html', {'submitted_email': email})
        except ProfileUser.DoesNotExist:
            messages.error(request,"Email not found")
            return render(request, 'auth/admin_forget_password.html', {'submitted_email': email})

        # if old otp have it will dlt
        OTPVerification.objects.filter(user=user).delete()
        otp =str(random.randint(1000, 9999))

        OTPVerification.objects.create(user=user,otp_code=otp,
            expires_at=timezone.now() +timedelta(minutes=2))

        
        send_mail(
    'Glowé Admin — OTP Verification',
    f'''
════════════════════════════════
              Glowé
         Admin Control Panel
════════════════════════════════

Hello Admin,

A login attempt was made to the Glowé Admin Control Panel.

Use the One-Time Password (OTP) below to verify your identity:

  ──────────────────────────
        Admin OTP

           {' '.join(str(otp))}

  This code is valid for 5 minutes.
  ──────────────────────────

SECURITY NOTICE:
- This OTP is strictly for admin access.
- Never share this code with anyone.
- If you did not initiate this login attempt, secure your account immediately and contact support.

For assistance, contact:
glowe639@gmail.com

════════════════════════════════
Regards,  
Glowé Team

© 2025 Glowé. All rights reserved.
Kerala, India — Admin Panel
════════════════════════════════
''',
    settings.EMAIL_HOST_USER,
    [email],
    fail_silently=False,
)

        request.session['reset_user']=user.id
        return redirect('admin_otp_verification')


    return render(request, 'auth/admin_forget_password.html', {'submitted_email': ''})

def admin_otp_verification(request):
    
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_dashboard')
    if request.user.is_authenticated:
        return redirect("home")
    
    user_id=request.session.get('reset_user')

    if not user_id:
        return redirect('admin_forgot_password')

    user=ProfileUser.objects.get(id=user_id)

    if request.method=="POST":
        entered_otp=request.POST.get('otp')

        otp_obj = OTPVerification.objects.filter(user=user).order_by('-created_at').first()

        if not otp_obj:
            messages.error(request,"OTP not found")
            return redirect('admin_otp_verification')

        if timezone.now() >otp_obj.expires_at:
            messages.error(request, "OTP expired")
            return redirect('admin_forgot_password')

        if otp_obj.otp_code!=entered_otp:
            messages.error(request,"Invalid OTP")
            return redirect('admin_otp_verification')

        otp_obj.is_verified =True
        otp_obj.save()

        otp_obj.delete() #delte otp ot[ is one ytime use]
        
        request.session['otp_verified']=True # delt otp aftr user cn still procced resset pass
        return redirect('admin_reset_password')

    return render(request,'auth/admin_otp_verification.html')


def admin_resend_otp(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_dashboard')
    if request.user.is_authenticated:
        return redirect("home")
    
    user_id=request.session.get('reset_user')
    if not user_id:
        return redirect('admin_forgot_password')

    user=ProfileUser.objects.get(id=user_id)

    OTPVerification.objects.filter(user=user).delete()
    otp =str(random.randint(1000,9999))


    OTPVerification.objects.create(user=user,otp_code=otp,
        expires_at=timezone.now() +timedelta(minutes=2))

    send_mail(
    'Glowé Admin — New OTP Requested',
    f'''
════════════════════════════════
              Glowé
         Admin Control Panel
════════════════════════════════

Hello Admin,

You requested a new OTP for the Glowé Admin Control Panel.

Your previous OTP has been cancelled.
Use the new code below to verify your identity:

  ──────────────────────────
        Admin OTP

           {' '.join(str(otp))}

  This code is valid for 5 minutes.
  ──────────────────────────

SECURITY NOTICE:
- This OTP is strictly for admin access.
- Never share this code with anyone.
- If you did not request a new OTP, secure your account immediately and contact support.

For assistance, contact:
glowe639@gmail.com
════════════════════════════════
© 2025 Glowé. All rights reserved.
Kerala, India — Admin Panel
════════════════════════════════
''',
    settings.EMAIL_HOST_USER,
    [user.email],
    fail_silently=False,
)
    messages.success(request,"New OTP sent")
    return redirect('admin_otp_verification')





def admin_reset_password(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_dashboard')
    if request.user.is_authenticated:
        return redirect("home")
    
    user_id=request.session.get('reset_user')
    verified=request.session.get('otp_verified')

    if not user_id or not verified:
        return redirect('admin_forgot_password')

    user=ProfileUser.objects.get(id=user_id)

    if request.method =="POST":
        password=request.POST.get('password')
        confirm=request.POST.get('confirm_password')

        if not password or not confirm:
            messages.error(request,"All fields required")
            return redirect('admin_reset_password')

        if password!=confirm:
            messages.error(request,"Passwords do not match")
            return redirect('admin_reset_password')

        
        pattern_pass=r'^(?=.*[A-Z])(?=.*[0-9])(?=.*[!@#$%^&*]).{8,}$'
        if not re.match(pattern_pass, password):
            messages.error(request,"Weak password")
            return redirect('admin_reset_password')

        user.set_password(password)
        user.save()

        # cleanup
        OTPVerification.objects.filter(user=user).delete()
        request.session.flush()

        messages.success(request,"Password reset successful")
        return redirect('admin_signin')

    return render(request, 'auth/admin_reset_password.html')

def user_management(request):
    q = request.GET.get('q', '')
    status = request.GET.get('status', '')
    

    users = ProfileUser.objects.filter(is_superuser=False).order_by('-date_joined')

    if q:
        users = users.filter(
            Q(full_name__icontains=q) |
            Q(email__icontains=q)
        )
    if status=='active':
        users=users.filter(is_active=True)
    elif status =='blocked':
        users =users.filter(is_active=False)

    paginator =Paginator(users, 5)
    page = request.GET.get('page', 1)
    page_obj = paginator.get_page(page)

    context={
        'users':page_obj,
        'page_obj': page_obj, 
        'q':q,
        'status':status,
    }
    

    return render(request, 'user_management.html',context)

def admin_toggle_block(request, id):
    if request.method !='POST':
        return redirect('user_management')
    user = get_object_or_404(ProfileUser, id=id)

    # Toggle is_activ
    
    user.is_active = not user.is_active
    user.save(update_fields=['is_active'])
    
    name=user.get_full_name() or user.email
    action='unblocked' if user.is_active else'blocked'
    messages.success(request,f"{name} has been {action} successfully.")

    return redirect('user_management')
def user_detail(request, id):
    user = get_object_or_404(ProfileUser, id=id, is_superuser=False)
 
    # Uncomment when Order model is ready:
    # from orders.models import Order
    # from django.db.models import Sum
    # all_orders   = Order.objects.filter(user=user).order_by('-created_at')
    # total_orders = all_orders.count()
    # total_spent  = all_orders.aggregate(s=Sum('total_amount'))['s'] or 0
    # avg_order    = round(total_spent / total_orders, 2) if total_orders else 0
    # orders_page  = Paginator(all_orders, 5).get_page(request.GET.get('order_page', 1))
 
    total_orders=0
    total_spent='0.00'
    avg_order='0.00'
    orders_page=    Paginator([], 5).get_page(1)
 
    return render(request,'user_detail.html',{
        'user':user,
        'total_orders':total_orders,
        'total_spent':total_spent,
        'avg_order':avg_order,
        'orders':orders_page,
    })
 