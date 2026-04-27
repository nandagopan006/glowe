from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from product.models import Product, Variant, Category
from order.models import Order, OrderItem, Payment
from django.apps import apps
ReturnRequest = apps.get_model('return', 'ReturnRequest')
from wallet.models import Wallet
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

User = get_user_model()

class ReturnTestCase(TestCase):
    @patch('product.models.resize_image')
    def setUp(self, mock_resize):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser@example.com', email='testuser@example.com', password='password123', is_verified=True
        )
        self.admin = User.objects.create_superuser(
            username='admin@example.com', email='admin@example.com', password='password123'
        )
        self.client.login(email='testuser@example.com', password='password123')
        
        self.category = Category.objects.create(name='Skincare', slug='skincare', is_active=True)
        self.product = Product.objects.create(name='Serum', slug='serum', category=self.category, is_active=True)
        self.variant = Variant.objects.create(
            product=self.product, size='30ml', sku='SERUM-30', price=1000.00, stock=10, is_active=True, is_default=True
        )
        
        # Create a delivered order
        self.order = Order.objects.create(
            user=self.user,
            order_number='ORD-101',
            total_amount=1000.00,
            subtotal=1000.00,
            order_status=Order.Status.DELIVERED,
            delivered_date=timezone.now() - timedelta(days=1)
        )
        self.payment = Payment.objects.create(order=self.order, payment_method=Payment.Method.RAZORPAY, payment_status='SUCCESS', amount=1000.00)
        self.item = OrderItem.objects.create(
            order=self.order, variant=self.variant, quantity=1, price_at_time=1000.00, item_status=OrderItem.Status.DELIVERED
        )

    def test_request_return_success(self):
        response = self.client.post(reverse('request_return', args=[self.item.id]), {
            'reason': 'Changed my mind',
            'condition': 'Unopened (Sealed)',
            'return_quantity': 1,
            'description': 'No longer need it'
        })
        self.assertRedirects(response, reverse('order_detail', args=[self.order.id]))
        self.assertEqual(ReturnRequest.objects.count(), 1)
        self.item.refresh_from_db()
        self.assertEqual(self.item.item_status, OrderItem.Status.RETURN_REQUESTED)

    def test_admin_approve_and_complete_return(self):
        # Setup return request
        r_req = ReturnRequest.objects.create(
            order_item=self.item, user=self.user, quantity=1, reason='Changed my mind', item_condition='Unopened (Sealed)'
        )
        self.item.item_status = OrderItem.Status.RETURN_REQUESTED
        self.item.save()
        
        self.client.login(email='admin@example.com', password='password123')
        
        # Approve
        self.client.post(reverse('approve_return', args=[r_req.id]))
        r_req.refresh_from_db()
        self.assertEqual(r_req.return_status, ReturnRequest.Status.APPROVED)
        
        # Schedule Pickup
        self.client.post(reverse('schedule_pickup', args=[r_req.id]), {'pickup_date': (timezone.now() + timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')})
        r_req.refresh_from_db()
        self.assertEqual(r_req.return_status, ReturnRequest.Status.PICKUP_SCHEDULED)
        
        # Mark Picked
        self.client.post(reverse('mark_picked', args=[r_req.id]))
        r_req.refresh_from_db()
        self.assertEqual(r_req.return_status, ReturnRequest.Status.PICKED_UP)
        
        # Complete (Refunds to wallet)
        self.client.post(reverse('complete_return', args=[r_req.id]))
        r_req.refresh_from_db()
        self.assertEqual(r_req.return_status, ReturnRequest.Status.COMPLETED)
        
        # Check wallet
        wallet = Wallet.objects.get(user=self.user)
        self.assertEqual(wallet.balance, Decimal('1000.00'))
        
        # Check item status
        self.item.refresh_from_db()
        self.assertEqual(self.item.item_status, OrderItem.Status.RETURNED)
