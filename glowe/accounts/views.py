from django.shortcuts import render,redirect
from django.http import HttpResponse
from .forms import SignupForm
from django.utils import timezone
import random 
from django.core.mail import send_mail
from django.conf import settings
from .models import ProfileUser


# logic of sigup page
def signup_page(request):
    
      # check if the form was submitted by the user
    if request.method == 'POST':
        
         # take the data sent from the signup form
        form = SignupForm(request.POST)
        
        if form.is_valid():   #check if all validations the form are correct 
            user= form.save(commit=False)           #create user objet and but not save in database
           
            user.username= user.email    # since we are not using username field in form
            
            #convert to hash the password
            user.set_password(form.cleaned_data['password'])
            
            # generate 4 digit otp
            otp=str(random.randint(1000,9999))
            user.otp=otp  # now user.otp = ex "482910"
            user.otp_create_at=timezone.now()
            user.is_active=False                 #user cannot login until otp  verfifed
            user.save()
            
            send_mail(         #used to sent mail otp                         #we  give it apattern sub,msg,from ,recipient
                'Your Glowé Verification Code', #subject=
                f'Your OTP is {otp}. It will expires in 3minutes. ',#message=
                settings.EMAIL_HOST_USER,# from_email=
                [user.email],#recipient_list for user
                
            )
            # in signup view — SAVE the email before redirecting
            request.session ['email']=user.email # it will store in broswer session
            
            return redirect('otp_verfication')
    else:
        # if the page is opened normally (GET request), create an empty form
        form = SignupForm()
  
    return render(request, "signup.html",{"form": form})



def signin_page(request):
    return render(request,'signin.html')




def forget_password(request):
    return render(request,'forget_password.html')




def otp_verfication(request):
    if request.method == 'POST':
        entered_otp=request.POSt.get('otp_code')   # get otp entered by user
        email=request.seesion.get('email')
        
        try:
            user = ProfileUser.objects.get(email=email)
        except ProfileUser.DoesNotExist:
            return redirect('signup')   # if user not found → send back to signup
        
        
        otp_age=timezone.now() - user.otp_create() #it calcut otp age
        
        if otp_age.seconds > 180 : #only 3min afther 3min it expires
            return render (request,'otp_varfication.html',
                           {'error',"OTP has expired. Please resend again."})
        
        if user.otp == entered_otp :
            user.is_verified= True
            user.is_active = True
            user.otp=None
            user.otp_created_at= None
            user.save()
            return redirect('signin')
        else:
            return render(request,'otp_verfication.htnl',
                          {'error':"Invalid OTP"})
        
            
        
    
    return render(request,'otp_verfication.html')



def reset_password(request):
    
    return render(request,'reset_password.html')