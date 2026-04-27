from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from coupons.models import Coupon, CouponUsage
from cart.models import Cart, CartItem
from product.models import Category, Product, Variant

User = get_user_model()

class CouponTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', email='test@example.com', password='password123')
        self.client.login(email='test@example.com', password='password123')
        
        self.today = timezone.now().date()
        self.coupon = Coupon.objects.create(
            code='TEST10',
            discount_type='flat',
            discount_value=Decimal('10.00'),
            min_purchase=Decimal('50.00'),
            total_usage_limit=1,
            usage_limit_per_user=1,
            start_date=self.today - timedelta(days=1),
            end_date=self.today + timedelta(days=10),
            is_active=True
        )

        category = Category.objects.create(name='Skincare', is_active=True)
        product = Product.objects.create(name='Test Product', slug='test-product', category=category, is_active=True)
        variant = Variant.objects.create(product=product, size='50ml', price=100.00, stock=10, is_active=True, is_default=True)
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, variant=variant, quantity=1)

    def test_apply_coupon_success(self):
        response = self.client.post(reverse('apply_coupon'), {'code': 'TEST10'})
        self.assertEqual(response.json()['success'], True)
        self.assertEqual(self.client.session.get('coupon_id'), self.coupon.id)
        
    def test_apply_coupon_min_purchase_fail(self):
        self.coupon.min_purchase = Decimal('200.00')
        self.coupon.save()
        response = self.client.post(reverse('apply_coupon'), {'code': 'TEST10'})
        self.assertEqual(response.json()['success'], False)
        
    def test_apply_coupon_expired(self):
        self.coupon.end_date = self.today - timedelta(days=2)
        self.coupon.save()
        response = self.client.post(reverse('apply_coupon'), {'code': 'TEST10'})
        self.assertEqual(response.json()['success'], False)
        
    def test_apply_coupon_usage_limit(self):
        self.coupon.used_count = 1
        self.coupon.save()
        response = self.client.post(reverse('apply_coupon'), {'code': 'TEST10'})
        self.assertEqual(response.json()['success'], False)
        
    def test_calculate_discount_with_race_condition_fix(self):
        from coupons.views import calculate_discount
        from django.http import HttpRequest
        from django.contrib.sessions.middleware import SessionMiddleware
        import importlib
        from django.conf import settings
        
        request = HttpRequest()
        request.user = self.user
        
        engine = importlib.import_module(settings.SESSION_ENGINE)
        request.session = engine.SessionStore()
        request.session['coupon_id'] = self.coupon.id
        request.session.save()
        
        discount = calculate_discount(request, Decimal('100.00'))
        self.assertEqual(discount, Decimal('10.00'))
        
        # Now simulate another user used it and bumped used_count
        self.coupon.used_count = 1
        self.coupon.save()
        
        # Recalculate discount should now return 0.00 and clear session
        discount = calculate_discount(request, Decimal('100.00'))
        self.assertEqual(discount, Decimal('0.00'))
        self.assertNotIn('coupon_id', request.session)
