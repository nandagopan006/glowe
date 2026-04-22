from django.shortcuts import render,redirect
from django.contrib.auth import authenticate,logout
# Create your views here.
def home(request):
    
    if  request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_dashboard')
    welcome= request.session.pop('welcome', None) 
    return render(request,'home.html',{'welcome':welcome})

def signout(request):
    logout(request)
    return redirect('signin')