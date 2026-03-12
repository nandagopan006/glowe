from django.shortcuts import render,redirect
from django.http import HttpResponse
from .forms import SignupForm
from django.utils import timezone
from datetime import timedelta
import random 
from django.core.mail import send_mail
from django.conf import settings

from .models import ProfileUser
from django.contrib.auth import authenticate,login

# logic of sigup page
def signup_page(request):
    
      # check if the form was submitted by the user
    if request.method == 'POST':
        
         # take the data sent from the signup form
        form = SignupForm(request.POST)
        
        if form.is_valid():   #check if all validations the form are correct 
            email = form.cleaned_data['email']
            existing_user = ProfileUser.objects.filter(
                email=email,is_verified=False).first()
            
            if existing_user :
                user = existing_user
                user.full_name = form.cleaned_data['full_name']
                user.set_password(form.cleaned_data['password'])#convert to hash the password 
                
            else:
                # create  new user
                user= form.save(commit=False)           #create user objet and but not save in database

                user.username= user.email    # since we are not using username field in form
            
            
            
            
            # generate 4 digit otp
            otp=str(random.randint(1000,9999))
            user.otp=otp  # now user.otp = ex "4910"
            user.otp_created_at=timezone.now()
            user.is_active=False   #user cannot login until otp  verfifed  
            user.save()
            
            send_mail(         #used to sent mail otp                         #we  give it apattern sub,msg,from ,recipient
                'Your Glowé Verification Code', #subject=
                f'Your OTP is {otp}. It will expires in 3minutes. ',#message=
                settings.EMAIL_HOST_USER,# from_email=
                [user.email],#recipient_list for user
                
            )
            # in signup view — SAVE the email before redirecting
            request.session ['email']=user.email # it will store in broswer session
            
            return redirect('signup_otp_verify')
    else:
        # if the page is opened normally (GET request), create an empty form
        form = SignupForm()
  
    return render(request, "signup.html",{"form": form})


def forget_password(request):
    return render(request,'forget_password.html')




def signup_otp_verify(request):
    email=request.session.get('email')
    
    try:
        user = ProfileUser.objects.get(email=email)
    except ProfileUser.DoesNotExist:
        return redirect('signup')   # if user not found → send back to signup
    
    
    otp_age=timezone.now() - user.otp_created_at #it calcut otp age
    used_time=round(otp_age.total_seconds())    # total seconds passed
    seconds_left=max(0,60 - used_time)    # seconds remaining
    
    

    #not verified user  (is_verified = False) no need to store datas so that
    expired_user = ProfileUser.objects.filter(
        is_verified = False ,otp_created_at__lt=timezone.now() - timedelta(minutes=5) #otp creat time <  current time MINUS 12 minutes vannalll
    )
    expired_user.delete()# delete  not verfied user  deatials  from db
            
    if request.method == 'POST':
        entered_otp=request.POST.get('otp')   # get otp entered by user    
        
        if used_time > 60 : #only 3min afther 3min it expires and if we enter incoorrect otp use the remaining time
            return render (request,'signup_otp_verify.html',
                           {'error':"OTP has expired. Please resend again.",
                            'seconds_left':0})
        
        if user.otp == entered_otp :
            user.is_verified= True
            user.is_active = True
            user.otp=None
            user.otp_created_at= None
            user.resend_count = 0            # reset resend count
            user.resend_blocked_until = None # reset block
            user.save()
            return redirect('home')
        else:
            return render(request,'signup_otp_verify.html',
                          {'error':"Invalid OTP",'seconds_left': seconds_left})
        
            
        
    
    return render(request,'signup_otp_verify.html',{'seconds_left':seconds_left})

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
            'error': f'Too many attempts. Try again after {remaining} minute(s).',
            'seconds_left': 0
        })

    # Check if currently blockedx
    if user.resend_blocked_until and timezone.now() >= user.resend_blocked_until:
        user.resend_blocked_until = None
        user.resend_count = 0

    # count reached 3  block
    if user.resend_count >= 3:
        user.resend_blocked_until = timezone.now() + timedelta(minutes=10)
        user.resend_count = 0
        user.save()
        return render(request, 'signup_otp_verify.html', {
            'error': 'Too many attempts. Try again after 10 minutes.',
            'seconds_left': 0
        })
        
        #  Success: Generate and save new OTP
    otp=str(random.randint(1000,9999))
    user.otp=otp
    user.otp_created_at=timezone.now()
    user.is_active=False
    user.resend_count += 1
    user.is_active = False
    user.save()
    
    send_mail(   #used to sent mail otp                 #we  give it apattern sub,msg,from ,recipient
            'Your Glowé Verification Code', #subject=
            f'Your OTP is {otp}. It will expires in 3minutes. ',#message=
            settings.EMAIL_HOST_USER,# from_email=
            [user.email],#recipient_list for user
    )   
    return redirect('signup_otp_verify')

def signin_page(request):
    
    if request.method == 'POST':
        email = request.POST.get('email','').strip().lower()
        password=request.POST.get('password')
        
        try: # check if email is exist or not
            user_obb=ProfileUser.objects.get(email=email)
        except ProfileUser.DoesNotExist:
            return render(request,'signin.html',{'error':'No account found with this email.'})
        # check if user is verified
        if not user_obb.is_verified :
            return render(request,'signin.html',{'error':'Please verify your email first.'})
            
        
        user = authenticate(request,username=user_obb.username,password=password)
        if user :
             #if  everything is correct   login
            login(request,user) # it create the seesion
            return redirect('home')
        else :
            # wrong password
             return render(request,'signin.html',{'error':'incorrect password.'})
      
           
               
    
    return render(request,'signin.html')


def otp_verfication(request):
    return render(request,'otp_verfication.html')
def reset_password(request):
    
    return render(request,'reset_password.html')