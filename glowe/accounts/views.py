from django.shortcuts import render,redirect
from django.http import HttpResponse
from .forms import SignupForm
from django.utils import timezone
from datetime import timedelta
import random 
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from .models import ProfileUser,OTPVerification
from django.contrib.auth import authenticate,login,logout
from django.urls import reverse 
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
import re




def signup_page(request):
    
    if request.user.is_authenticated:
        return redirect('home')
    
      
    if request.method == 'POST':
        
         # take the data sent from the signup form
        form = SignupForm(request.POST)
        
        if form.is_valid():    
            email = form.cleaned_data['email']
            existing_user = ProfileUser.objects.filter(
            email=email,is_verified=False).first()
            password = form.cleaned_data['password']
            
            if existing_user :
                user = existing_user
                user.full_name = form.cleaned_data['full_name']
                user.username = user.email
                user.set_password(password)
                
                
            else:
                # create  new user
                user= form.save(commit=False)           #create user objet and but not save in database

                user.username= user.email   
                user.set_password(password)
            
            
      
            user.is_active=False
            user.is_verified = False
            user.save()
            
            OTPVerification.objects.filter(user=user, is_verified=False).delete()
            
            otp_code= str(random.randint(1000, 9999))
            OTPVerification.objects.create(user= user,otp_code= otp_code,
                    expires_at =timezone.now() + timedelta(minutes=1),)
            
            send_mail(
    'Verify Your Glowé Account',
    f'''
Dear {user.full_name or user.email.split('@')[0].capitalize()},

We received a request to verify your account.

Your One-Time Password (OTP) is:

{''.join(otp_code)}

This code is valid for 1 minute.

If you did not request this verification, please ignore this email.

For assistance, contact:
glowe639@gmail.com

Regards,  
Glowé Team
''',
    settings.EMAIL_HOST_USER,
    [user.email],
    fail_silently=False,
)
            # in signup view — SAVE the email before redirecting
            request.session ['email']=user.email # it will store in broswer session
            request.session['otp_msg'] = 'OTP sent! Check your email.' 
            
            return redirect('signup_otp_verify')
    else:
        # if the page is opened normally (GET request), create an empty form
        form = SignupForm()
  
    return render(request, "signup.html",{"form": form})



def signup_otp_verify(request):
    email=request.session.get('email')
    otp_msg = request.session.pop('otp_msg', None)
    
    try:
        user = ProfileUser.objects.get(email=email)
    except ProfileUser.DoesNotExist:
        return redirect('signup')  
    
    
    # get the latest unverified OTP record for this user
    otp_record = OTPVerification.objects.filter(user=user,is_verified=False).first()    
    
    if not otp_record:
        return redirect('signup') 

    #seconds remaining for the timer start with remaing
    seconds_left =max(0,round((otp_record.expires_at - timezone.now()).total_seconds()))
    # delete expired OTP records 
    OTPVerification.objects.filter(
        is_verified=False,
        created_at__lt=timezone.now() - timedelta(minutes=5) #to keep database clean (5m)
    ).delete()
    
    if request.method == 'POST':
        entered_otp=request.POST.get('otp')   # get otp entered by user    
        
        # check if OTP  expired ayyo — current time 
        if timezone.now() > otp_record.expires_at:
            return render(request, 'signup_otp_verify.html', {
                'error': 'OTP has expired. Please resend again.','seconds_left': 0,'submitted_otp': entered_otp, })
        
        if otp_record.otp_code == entered_otp :
            
            # mark as verfied
            otp_record.is_verified = True
            otp_record.save()
            
            user.is_verified= True
            user.is_active = True
            user.resend_count = 0            # reset resend count
            user.resend_blocked_until = None # reset block
            user.save()
            
            request.session['success_msg'] = 'Account created Successfully  !'
            return redirect('signin')
        else:
            return render(request,'signup_otp_verify.html',
                          {'error':"Invalid OTP",'seconds_left': seconds_left,'submitted_otp': entered_otp, })
        
    return render(request,'signup_otp_verify.html',{'seconds_left':seconds_left,'otp_msg': otp_msg,})

def signup_resend_otp(request):
    email=request.session.get('email')
    
    try:
        user =ProfileUser.objects.get(email=email)
    except ProfileUser.DoesNotExist:
        return redirect('signup')
    
     # check if blocked
    if user.resend_blocked_until and timezone.now() < user.resend_blocked_until:
        remaining = round((user.resend_blocked_until - timezone.now()).total_seconds() / 60)
        return render(request, 'signup_otp_verify.html', {
        'error': f'Too many attempts. Try again after {remaining} minute(s).','seconds_left': 0})

    # Check if currently block and reset
    if user.resend_blocked_until and timezone.now() >= user.resend_blocked_until:
        user.resend_blocked_until = None
        user.resend_count = 0


    if user.resend_count >= 3:
        user.resend_blocked_until = timezone.now() + timedelta(minutes=10)
        user.resend_count = 0
        user.save()
        
        return render(request, 'signup_otp_verify.html',{
        'error': 'Too many attempts. Try again after 10 minutes.','seconds_left': 0})
        
   
    OTPVerification.objects.filter(user=user, is_verified=False).delete()
 
    otp_code = str(random.randint(1000, 9999))
    OTPVerification.objects.create(user= user,otp_code= otp_code,
        expires_at = timezone.now() + timedelta(minutes=1))
    
    user.is_active    = False
    user.resend_count += 1
    user.save()
    
    send_mail(
    'Verify Your Glowé Account',
    f'''
════════════════════════════════
              Glowé
      Your Natural Beauty Store
════════════════════════════════

Dear {user.full_name or user.email.split('@')[0].capitalize()},

We received a request to verify your Glowé account.

Please use the One-Time Password (OTP) below:

  ──────────────────────────
        Verification Code

         {' '.join(otp_code)}

  Valid for 1 minute
  ──────────────────────────

SECURITY NOTICE:
Do not share this code with anyone.
Glowé will never request your OTP.

If you did not request this, you may ignore this email.

────────────────────────────────
For assistance, contact:
glowe639@gmail.com
────────────────────────────────

════════════════════════════════
Regards,  
Glowé Team

© 2025 Glowé. All rights reserved.
════════════════════════════════
''',
    settings.EMAIL_HOST_USER,
    [user.email],
    fail_silently=False,
)
    
    request.session['otp_msg'] = 'New OTP sent to your email.'   
    return redirect('signup_otp_verify')


def signin_page(request):
    
    if request.user.is_authenticated:
        return redirect('home')
    success_msg = request.session.pop('success_msg', None)
    update_password=request.session.pop('update_password',None)
    if request.method == 'POST':
        email = request.POST.get('email','').strip().lower()
        password=request.POST.get('password')
        
        if not email:
            return render(request,'signin.html',{'error':'Please enter your email.'})
        
        if not password:
            return render(request,'signin.html',{'error':'Please enter your password.','submitted_email': email,})

        
        try: # check ifexist or not
            user_obb=ProfileUser.objects.get(email=email)
        except ProfileUser.DoesNotExist:
            return render(request,'signin.html',{'error':'No account found with this email.','submitted_email': email,})
        
        #email 
        if not user_obb.is_verified :
            return render(request,'signin.html',{'error':'Your email is not verified. Please complete signup first.','submitted_email': email,})
        
        if not user_obb.is_active:
            return render(request, 'signin.html', {'error': 'Your account is disabled. Please contact support.','submitted_email': email,})
    
        
        user = authenticate(request, username=email, password=password)
        
        if user :
             #if  everything is correct   login
            login(request,user) # it create the seesion
            request.session['welcome']='Welcome to Glowé.  !'
            return redirect('home')
        else :
             return render(request,'signin.html',{'error':'Invalid credentials.','submitted_email': email,})
      
    return render(request,'signin.html',{'success_msg': success_msg,'update_password':update_password})

def forget_password(request):

    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        email =request.POST.get('email')

        try:
            user=ProfileUser.objects.get(email=email)

            if user.is_active and user.is_verified:  #both checks
                # check block FIRST before anything else
                if user.reset_block_until and timezone.now() < user.reset_block_until:
                    
                        # still blocked  do not send email
                    remaining_minutes = round((user.reset_block_until - timezone.now()).total_seconds() / 60)
                    return render(request, 'forget_password.html', {
                        'error': f'Too many attempts. Please try again after {remaining_minutes} minute(s).','submitted_email':email})
                    
                #save user first before generating token
                user.reset_attempts = 0  
                user.reset_block_until = None # fresh request remove any existing block
                user.save()
                
                uid   = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)
                
                user.reset_token = token 
                user.reset_requested_at=timezone.now()
                user.save() 

                
                #  reset link
                reset_link = request.build_absolute_uri(
                    reverse('reset_password', kwargs={'uidb64': uid, 'token': token}))
                
                send_mail(
    'Reset Your Glowé Password',
    f'''
════════════════════════════════
              Glowé
      Your Natural Beauty Store
════════════════════════════════

Dear {user.full_name or user.email.split('@')[0].capitalize()},

We received a request to reset the password for your Glowé account.

Please click the link below to reset your password:

  ──────────────────────────
  {reset_link}
  ──────────────────────────

This link will expire in 15 minutes.

SECURITY NOTICE:
- If you did not request a password reset, please ignore this email.
- Never share this link with anyone, including Glowé staff.

────────────────────────────────
For assistance, contact:
glowe639@gmail.com
────────────────────────────────
© 2025 Glowé. All rights reserved.
Kerala, India
════════════════════════════════
''',
    settings.EMAIL_HOST_USER,
    [user.email],
    fail_silently=False,
)
                
                request.session['reset_email'] = user.email
               
                return redirect('forget_password_link')

            else:
                return render(request, 'forget_password.html', {
                    'error': 'Please verify your email before resetting your password.','submitted_email':email})

        except ProfileUser.DoesNotExist:
            return render(request, 'forget_password.html', {
                'error': 'No account found with this email.','submitted_email':email})

    return render(request, 'forget_password.html')

def forget_password_link(request):
    email= request.session.get('reset_email', '')
    
    if not email:
        return redirect('forget_password')
 
    try:
        user = ProfileUser.objects.get(email=email)
    except ProfileUser.DoesNotExist:
        return redirect('forget_password')
    
   
    is_blocked =False
    remaining_minutes= 0
    max_reached= False
 
    # check if a block exists in the database for this user
    if user.reset_block_until:
        if timezone.now() < user.reset_block_until:
           
            is_blocked= True
            remaining_minutes =round((user.reset_block_until-timezone.now()).total_seconds() / 60)
            max_reached=True
        else:
            
            user.reset_attempts = 0 
            user.reset_block_until= None 
            user.save()
 
    return render(request, 'forget_password_link.html', {
        'email':email,'is_blocked':is_blocked,'remaining_minutes':remaining_minutes,
        'resent_count':user.reset_attempts,'max_reached':max_reached,})


def resend_reset_email(request):
    email = request.session.get('reset_email')
    
    if not email :
        return redirect('forget_password')
    
    try :
        user=ProfileUser.objects.get(email=email)
    except ProfileUser.DoesNotExist :
        return redirect('forget_password')

    if user.reset_block_until:
        if timezone.now() < user.reset_block_until:
        
            remaining_minutes = round((user.reset_block_until - timezone.now()).total_seconds() / 60)
            messages.warning(request, f'Too many attempts. Try again after {remaining_minutes} minute(s).')
            return redirect('forget_password_link')
        else:
          
            user.reset_attempts= 0
            user.reset_block_until=None
            user.save()
 
    if user.reset_attempts >= 3:
        user.reset_block_until=timezone.now() + timedelta(minutes=15)
        user.reset_attempts=0
        user.save()
        messages.warning(request, 'Too many attempts. Try again after 15 minutes.')
        return redirect('forget_password_link')
    
    user.reset_attempts +=1  
    user.save()
 
    #generate new token and save in database
    uid=urlsafe_base64_encode(force_bytes(user.pk))
    token =default_token_generator.make_token(user)  
 
    user.reset_token= token
    user.reset_requested_at= timezone.now() 
    user.save()
 
    # reset link new 
    reset_link = request.build_absolute_uri(
        reverse('reset_password', kwargs={'uidb64': uid, 'token': token}))
 
    send_mail(
    'Reset Your Glowé Password',
    f'''
════════════════════════════════
              Glowé
      Your Natural Beauty Store
════════════════════════════════

Dear {user.full_name or user.email.split('@')[0].capitalize()},

We received a request to reset the password for your Glowé account.

Please click the link below to reset your password:

  ──────────────────────────
  {reset_link}
  ──────────────────────────

This link will expire in 15 minutes.

SECURITY NOTICE:
- If you did not request a password reset, please ignore this email.
- Never share this link with anyone, including Glowé staff.

────────────────────────────────
For assistance, contact:
glowe639@gmail.com
────────────────────────────────
© 2025 Glowé. All rights reserved.
Kerala, India
════════════════════════════════
''',
    settings.EMAIL_HOST_USER,
    [user.email],
    fail_silently=False,
) 
    messages.success(request, 'Reset link sent to your email.')
    return redirect('forget_password_link')


def reset_password(request,uidb64,token):
    
    if request.user.is_authenticated:
        return redirect('home')
    
    
    try :
        uid= force_str(urlsafe_base64_decode(uidb64))
        user = ProfileUser.objects.get(pk=uid) 
    except ProfileUser.DoesNotExist:
        return redirect('reset_password_invalid')
    
     
    if user.reset_token is None or user.reset_token != token:
        return redirect('reset_password_invalid')
 
    if user.reset_requested_at is None:
        return redirect('reset_password_invalid')
 
    expiry_time=user.reset_requested_at +timedelta(minutes=15)
    if timezone.now() > expiry_time:

        user.reset_token=None
        user.reset_requested_at= None
        user.save()
        return redirect('reset_password_invalid') 
    
    if request.method == 'POST':
        
        new_password     = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        # password validation
        pattern_password=r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$'
        if not re.match(pattern_password, new_password):
            return render(request, "reset_password.html", {
                    "error": "Password must contain upper,lower,number(8+ chars)",'uidb64': uidb64,'token':  token,})
            
        if new_password != confirm_password :
            return render(request,'reset_password.html', {'error': 'Passwords do not match.',
                'uidb64': uidb64, 'token': token,})
            
            
    
        user.set_password(new_password)
        
        #clear reset token appo enii link chayan paatilla  allam clear chaayumm
        user.reset_token = None
        user.reset_requested_at=None
        user.reset_attempts =0
        user.reset_block_until= None
        user.save()
        
        request.session['update_password']='SuccessFully Updated The Password'
        messages.success(request, 'Password reset successful. Please sign in.')
        return redirect('signin')

    return render(request,'reset_password.html' ,{'uidb64': uidb64,'token':  token,})

def reset_password_invalid(request):
    return render(request,'reset_password_invalid.html')


