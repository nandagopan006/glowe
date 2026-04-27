from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from product.models import Category, Product, Variant
from order.models import Order, OrderItem, ShippingAddress, Payment
from cart.models import Cart, CartItem
from user.models import Address
from decimal import Decimal

User = get_user_model()

class OrderTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', email='test@example.com', password='password123', first_name='Test', last_name='User')
        
        self.category = Category.objects.create(name='Skincare', is_active=True)
        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            category=self.category,
            description='Test Description',
            is_active=True
        )
        self.variant = Variant.objects.create(
            product=self.product,
            size='50ml',
            price=100.00,
            stock=10,
            is_active=True,
            is_default=True
        )
        
        self.address = Address.objects.create(
            user=self.user,
            full_name='Test User',
            phone_number='1234567890',
            street_address='123 Test St',
            city='Test City',
            state='Test State',
            pincode='123456',
            country='India'
        )
        
        self.cart = Cart.objects.create(user=self.user)
        self.cart_item = CartItem.objects.create(cart=self.cart, variant=self.variant, quantity=2)

    def test_place_order_cod(self):
        self.client.login(email='test@example.com', password='password123')
        
        # We need to simulate POST to place_order
        response = self.client.post(reverse('place_order'), {
            'address_id': self.address.id,
            'payment_method': 'COD'
        })
        
        # Should redirect to order success
        self.assertEqual(response.status_code, 302)
        
        order = Order.objects.filter(user=self.user).first()
        self.assertIsNotNone(order)
        self.assertEqual(order.order_status, Order.Status.CONFIRMED)
        
        # Stock should be reduced by 2
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 8)
        
        # Cart should be empty
        self.assertEqual(self.cart.items.count(), 0)

    def test_place_order_exceed_stock(self):
        self.client.login(email='test@example.com', password='password123')
        
        # Exceed stock in cart
        self.cart_item.quantity = 15
        self.cart_item.save()
        
        response = self.client.post(reverse('place_order'), {
            'address_id': self.address.id,
            'payment_method': 'COD'
        })
        
        # Should redirect to cart with error
        self.assertRedirects(response, reverse('cart'))
        
        # No order created
        self.assertEqual(Order.objects.filter(user=self.user).count(), 0)
        
        # Stock should be 10
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 10)

    def test_cancel_order(self):
        self.client.login(email='test@example.com', password='password123')
        
        # Place order first
        self.client.post(reverse('place_order'), {
            'address_id': self.address.id,
            'payment_method': 'COD'
        })
        
        order = Order.objects.filter(user=self.user).first()
        
        # Cancel the order
        response = self.client.post(reverse('cancel_order', args=[order.id]), {
            'reason': 'Changed my mind'
        })
        
        self.assertEqual(response.status_code, 302)
        
        order.refresh_from_db()
        self.assertEqual(order.order_status, Order.Status.CANCELLED)
        
        # Stock should be restored (10 - 2 + 2 = 10)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 10)

    def test_cancel_order_item_partial(self):
        self.client.login(email='test@example.com', password='password123')
        
        # Place order
        self.client.post(reverse('place_order'), {
            'address_id': self.address.id,
            'payment_method': 'COD'
        })
        
        order = Order.objects.filter(user=self.user).first()
        item = order.items.first()
        
        # Cancel 1 out of 2 items
        response = self.client.post(reverse('cancel_order_item', args=[item.id]), {
            'quantity': 1,
            'reason': 'Do not need 2'
        })
        
        self.assertEqual(response.status_code, 302)
        
        # We should have 2 OrderItems now (1 active, 1 cancelled)
        self.assertEqual(order.items.count(), 2)
        
        # Stock should be 9 (10 - 2 + 1)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 9)
