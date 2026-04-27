from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from product.models import Product, Variant, Category
from wishlist.models import Wishlist, StockNotification
from cart.models import Cart, CartItem
from unittest.mock import patch

User = get_user_model()

class WishlistTestCase(TestCase):
    @patch('product.models.resize_image')
    def setUp(self, mock_resize):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser@example.com',
            email='testuser@example.com',
            password='password123',
            is_verified=True,
            is_active=True
        )
        self.client.login(email='testuser@example.com', password='password123')
        
        self.category = Category.objects.create(name='Test Category', slug='test-cat', is_active=True)
        self.product = Product.objects.create(name='Test Product', slug='test-prod', category=self.category, is_active=True)
        self.variant = Variant.objects.create(
            product=self.product, size='50ml', sku='TEST-01', price=100.00, stock=10, is_active=True, is_default=True
        )

    def test_toggle_wishlist(self):
        # Add to wishlist
        response = self.client.post(reverse('toggle_wishlist', args=[self.variant.id]))
        self.assertEqual(Wishlist.objects.count(), 1)
        self.assertRedirects(response, reverse('wishlist'), fetch_redirect_response=False)
        
        # Remove from wishlist (toggle again)
        response = self.client.post(reverse('toggle_wishlist', args=[self.variant.id]))
        self.assertEqual(Wishlist.objects.count(), 0)

    def test_remove_from_wishlist(self):
        Wishlist.objects.create(user=self.user, variant=self.variant)
        self.assertEqual(Wishlist.objects.count(), 1)
        
        response = self.client.post(reverse('remove_from_wishlist', args=[self.variant.id]))
        self.assertEqual(Wishlist.objects.count(), 0)

    def test_clear_wishlist(self):
        Wishlist.objects.create(user=self.user, variant=self.variant)
        response = self.client.post(reverse('clear_wishlist'))
        self.assertEqual(Wishlist.objects.count(), 0)

    def test_move_to_cart(self):
        Wishlist.objects.create(user=self.user, variant=self.variant)
        response = self.client.post(reverse('move_to_cart', args=[self.variant.id]))
        
        # Item should be in cart
        self.assertEqual(CartItem.objects.filter(cart__user=self.user, variant=self.variant).count(), 1)
        # Item should be removed from wishlist
        self.assertEqual(Wishlist.objects.count(), 0)

    def test_notify_me(self):
        self.variant.stock = 0
        self.variant.save()
        
        response = self.client.post(reverse('notify_me', args=[self.variant.id]))
        self.assertEqual(StockNotification.objects.filter(user=self.user, variant=self.variant).count(), 1)
