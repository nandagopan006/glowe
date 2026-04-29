from django import forms 
from .models import ProfileUser
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
import re


class SignupForm(forms.ModelForm):
    email = forms.EmailField(required=True)
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)
    referral_code = forms.CharField(required=False)
    
    class Meta:
        model = ProfileUser
        fields = ["full_name", "email", "referral_code"]
        
        
    #ull_name validation
    def clean_full_name(self):
        
        full_name=self.cleaned_data.get('full_name','').strip()    # # get full_name and remove extra spaces from start and end
       
        if len(full_name) < 4:
            raise forms.ValidationError('Full name must be at least 4 characters.')
        
    
        if '  ' in full_name:
            raise forms.ValidationError('Full name must not contain double spaces.')
        
        # remove  extra space for temp checking, only alphabets allowed
        if not full_name.replace(' ','').isalpha():
            raise forms.ValidationError('Full name can only contain letters.')
            
        return full_name
                
    # email validation
    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if re.match(r"^\*+@gmail\.com$", email):
            raise forms.ValidationError("Masked email is not allowed")

        existing = ProfileUser.objects.filter(email=email).first()
        if existing and existing.is_verified:
            raise forms.ValidationError("Email already registered")

        return email



 
    
    #password vlidation
    def clean_password(self):
        password=self.cleaned_data.get("password")
            
 
        pattern = r'^(?=.*[A-Z])(?=.*[0-9])(?=.*[@!#$%&*]).{8,}$'
        
        if not re.match(pattern,password):
            raise forms.ValidationError(
                'Password must be at least 8 characters, include one uppercase letter, one number, and one special character (@!#$%&*).'
            )
        try:
            validate_password(password)
        except ValidationError as e:
            raise forms.ValidationError(e.messages)
        
        return password
    

    # Password match validation
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match")

        return cleaned_data
