from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from cart.models import Cart, CartItem
from product.models import Category, Product, Variant
from decimal import Decimal

User = get_user_model()

class CartTestCase(TestCase):
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
        
        self.product2 = Product.objects.create(
            name='Test Product 2',
            slug='test-product-2',
            category=self.category,
            description='Test Description 2',
            is_active=True
        )
        self.variant2 = Variant.objects.create(
            product=self.product2,
            size='100ml',
            price=50.00,
            stock=2,
            is_active=True,
            is_default=True
        )
        
    def test_cart_creation(self):
        cart = Cart.objects.create(user=self.user)
        self.assertEqual(cart.user, self.user)
        
    def test_add_to_cart_authenticated(self):
        self.client.login(email='test@example.com', password='password123')
        response = self.client.post(reverse('add_to_cart'), {
            'variant_id': self.variant.id,
            'quantity': 2
        })
        self.assertEqual(response.status_code, 302)
        
        cart = Cart.objects.get(user=self.user)
        self.assertEqual(cart.items.count(), 1)
        item = cart.items.first()
        self.assertEqual(item.variant, self.variant)
        self.assertEqual(item.quantity, 2)
        
    def test_add_to_cart_exceed_stock(self):
        self.client.login(email='test@example.com', password='password123')
        response = self.client.post(reverse('add_to_cart'), {
            'variant_id': self.variant2.id,
            'quantity': 3 # stock is 2
        })
        cart = Cart.objects.get(user=self.user)
        self.assertEqual(cart.items.count(), 0) # Should fail and not add
        
    def test_update_cart(self):
        self.client.login(email='test@example.com', password='password123')
        cart = Cart.objects.create(user=self.user)
        item = CartItem.objects.create(cart=cart, variant=self.variant, quantity=1)
        
        response = self.client.post(reverse('update_cart'), {
            'item_id': item.id,
            'quantity': 3
        })
        self.assertEqual(response.status_code, 302)
        item.refresh_from_db()
        self.assertEqual(item.quantity, 3)
        
    def test_update_cart_exceed_stock(self):
        self.client.login(email='test@example.com', password='password123')
        cart = Cart.objects.create(user=self.user)
        item = CartItem.objects.create(cart=cart, variant=self.variant2, quantity=1)
        
        response = self.client.post(reverse('update_cart'), {
            'item_id': item.id,
            'quantity': 3 # stock is 2
        })
        item.refresh_from_db()
        self.assertEqual(item.quantity, 2) # should be capped at stock
        
    def test_remove_from_cart(self):
        self.client.login(email='test@example.com', password='password123')
        cart = Cart.objects.create(user=self.user)
        item = CartItem.objects.create(cart=cart, variant=self.variant, quantity=1)
        
        response = self.client.post(reverse('remove_from_cart', args=[item.id]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(CartItem.objects.count(), 0)
        
    def test_cart_view(self):
        self.client.login(email='test@example.com', password='password123')
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, variant=self.variant, quantity=2)
        
        response = self.client.get(reverse('cart'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Product')
        
    def test_checkout_empty_cart(self):
        self.client.login(email='test@example.com', password='password123')
        Cart.objects.create(user=self.user)
        response = self.client.get(reverse('checkout'))
        # Should redirect back to cart
        self.assertRedirects(response, reverse('cart'))
