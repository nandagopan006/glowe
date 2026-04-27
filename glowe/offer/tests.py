from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from product.models import Product, Variant, Category
from offer.models import Offer, OfferItem
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

class OfferTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_superuser(
            username='admin@example.com',
            email='admin@example.com',
            password='password123'
        )
        self.client.login(email='admin@example.com', password='password123')
        
        self.category = Category.objects.create(name='Skincare', slug='skincare', is_active=True)
        self.product = Product.objects.create(name='Serum', slug='serum', category=self.category, is_active=True)
        self.variant = Variant.objects.create(
            product=self.product, size='30ml', sku='SERUM-30', price=1000.00, stock=10, is_active=True, is_default=True
        )

    def test_create_product_offer(self):
        response = self.client.post(reverse('add_offer'), {
            'name': 'Test Offer',
            'discount_type': 'PERCENTAGE',
            'discount_value': '10',
            'max_discount': '100',
            'start_date': timezone.now().strftime('%Y-%m-%d'),
            'end_date': (timezone.now() + timedelta(days=5)).strftime('%Y-%m-%d'),
            'apply_to': 'PRODUCT',
            'product_id': self.product.id,
            'is_active': 'on'
        })
        self.assertEqual(Offer.objects.count(), 1)
        self.assertEqual(OfferItem.objects.filter(apply_to='PRODUCT').count(), 1)

    def test_calculate_best_offer(self):
        from offer.utils import get_best_offer
        
        # Create a 10% product offer
        offer1 = Offer.objects.create(
            name='Prod Offer', discount_type='PERCENTAGE', discount_value=10,
            start_date=timezone.now(), end_date=timezone.now() + timedelta(days=5), is_active=True
        )
        OfferItem.objects.create(offer=offer1, apply_to='PRODUCT', product=self.product)
        
        # Create a 20% category offer
        offer2 = Offer.objects.create(
            name='Cat Offer', discount_type='PERCENTAGE', discount_value=20,
            start_date=timezone.now(), end_date=timezone.now() + timedelta(days=5), is_active=True
        )
        OfferItem.objects.create(offer=offer2, apply_to='CATEGORY', category=self.category)
        
        best_offer, best_discount = get_best_offer(self.product, Decimal('1000.00'))
        
        # Should pick the 20% offer (200.00 discount)
        self.assertEqual(best_offer, offer2)
        self.assertEqual(best_discount, Decimal('200.00'))
