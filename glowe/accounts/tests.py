from django.test import TestCase, Client
from django.urls import reverse
from django.core import mail
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from .models import ProfileUser, OTPVerification
from .forms import SignupForm
from wallet.models import Wallet
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp

User = get_user_model()

class AccountsTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.signup_url = reverse('signup')
        self.signin_url = reverse('signin')
        self.otp_verify_url = reverse('signup_otp_verify')
        self.forget_password_url = reverse('forget_password')
        
        # Create a dummy SocialApp for allauth template tags
        site = Site.objects.get_current()
        if not SocialApp.objects.filter(provider='google').exists():
            social_app = SocialApp.objects.create(
                provider='google',
                name='Google',
                client_id='dummy',
                secret='dummy'
            )
            social_app.sites.add(site)

    # ====================== MODEL TESTS ======================
    def test_create_user_and_referral_code(self):
        user = User.objects.create_user(
            username="testuser@example.com",
            email="testuser@example.com",
            password="TestPass123!",
            full_name="Test User"
        )
        self.assertTrue(user.referral_code)  # auto-generated
        self.assertEqual(len(user.referral_code), 8)

    def test_otp_verification_model(self):
        user = User.objects.create_user(username="otpuser@test.com", email="otpuser@test.com", password="Pass123!")
        otp = OTPVerification.objects.create(
            user=user,
            otp_code="1234",
            expires_at=timezone.now() + timedelta(minutes=5)
        )
        self.assertFalse(otp.is_verified)
        self.assertTrue(otp.expires_at > timezone.now())

    # ====================== FORM TESTS ======================
    def test_signup_form_valid(self):
        form_data = {
            'full_name': 'John Doe',
            'email': 'john@example.com',
            'phone_number': '9876543210',
            'password': 'TestPass123!',
            'confirm_password': 'TestPass123!',
        }
        form = SignupForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_signup_form_invalid_password(self):
        form_data = {
            'full_name': 'John Doe',
            'email': 'john@example.com',
            'password': 'weak',
            'confirm_password': 'weak',
        }
        form = SignupForm(data=form_data)
        self.assertFalse(form.is_valid())

    # ====================== VIEW / FLOW TESTS ======================
    def test_signup_creates_unverified_user_and_sends_otp(self):
        response = self.client.post(self.signup_url, {
            'full_name': 'Test User',
            'email': 'newuser@example.com',
            'phone_number': '1234567890',
            'password': 'StrongPass123!',
            'confirm_password': 'StrongPass123!',
        })
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(email='newuser@example.com')
        self.assertFalse(user.is_verified)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Verification Code', mail.outbox[0].subject)

    def test_otp_verification_success(self):
        user = User.objects.create_user(username="otpuser2@test.com", email="otpuser2@test.com", password="Pass123!", is_verified=False)
        otp_obj = OTPVerification.objects.create(
            user=user,
            otp_code="5678",
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        
        session = self.client.session
        session['email'] = user.email
        session.save()

        response = self.client.post(self.otp_verify_url, {'otp': '5678'})
        user.refresh_from_db()
        self.assertTrue(user.is_verified)
        self.assertRedirects(response, self.signin_url)

    def test_signin_unverified_user(self):
        user = User.objects.create_user(
            username='testuser@example.com',
            email='testuser@example.com',
            password='password123',
            full_name='Test User',
            is_verified=False
        )
        response = self.client.post(self.signin_url, {
            'email': 'testuser@example.com',
            'password': 'password123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Your email is not verified')

    def test_referral_bonus_on_signup_verification(self):
        referrer = User.objects.create_user(
            username='referrer@example.com',
            email='referrer@example.com',
            password='password123',
            full_name='Referrer User',
            is_verified=True
        )
        new_user = User.objects.create_user(
            username='new@example.com',
            email='new@example.com',
            password='password123',
            is_verified=False,
            referred_by=referrer
        )
        OTPVerification.objects.create(
            user=new_user,
            otp_code='1234',
            expires_at=timezone.now() + timedelta(minutes=5)
        )
        
        session = self.client.session
        session['email'] = 'new@example.com'
        session.save()
        
        response = self.client.post(self.otp_verify_url, {'otp': '1234'})
        self.assertRedirects(response, reverse('signin'))
        
        referrer.refresh_from_db()
        self.assertEqual(referrer.referral_count, 1)
        wallet = Wallet.objects.get(user=referrer)
        self.assertEqual(wallet.balance, 500)
