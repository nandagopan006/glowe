from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from product.models import Product, Variant, Category, ProductImage
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch
import json

User = get_user_model()

class ProductTestCase(TestCase):
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
        self.admin = User.objects.create_superuser(
            username='admin@example.com',
            email='admin@example.com',
            password='password123'
        )
        self.category = Category.objects.create(name='Skincare', slug='skincare', is_active=True)
        self.product = Product.objects.create(
            name='Face Wash',
            category=self.category,
            description='Good face wash showing more than twelve characters.',
            ingredients='Water, Soap',
            how_to_use='Wash face',
            skin_type='Oily',
            is_active=True
        )
        self.variant = Variant.objects.create(
            product=self.product,
            size='100ml',
            price=200.00,
            stock=50,
            is_active=True,
            is_default=True
        )
        # Create a dummy image (1x1 GIF)
        gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        img = SimpleUploadedFile("test_image.jpg", gif, content_type="image/jpeg")
        self.image = ProductImage.objects.create(
            product=self.product,
            image=img,
            is_primary=True
        )

    # ====================== MODEL TESTS ======================
    def test_product_slug_auto_gen(self):
        self.assertEqual(self.product.slug, 'face-wash')
        p2 = Product.objects.create(name='Face Wash', category=self.category, description='Desc for product two')
        self.assertEqual(p2.slug, 'face-wash-1')

    def test_variant_sku_auto_gen(self):
        self.assertEqual(self.variant.sku, 'FACE-WASH-100ML')
        v2 = Variant.objects.create(product=self.product, size='100ml', price=250.00, stock=10)
        self.assertEqual(v2.sku, 'FACE-WASH-100ML-1')

    # ====================== VIEW TESTS (USER) ======================
    def test_product_listing(self):
        response = self.client.get(reverse('product_listing'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Face Wash')

    def test_product_detail_view(self):
        response = self.client.get(reverse('product_detail_view', args=[self.product.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Face Wash')

    # ====================== ADMIN TESTS ======================
    def test_product_management_access(self):
        self.client.login(email='admin@example.com', password='password123')
        response = self.client.get(reverse('product_management'))
        self.assertEqual(response.status_code, 200)

    def test_add_product_submission(self):
        self.client.login(email='admin@example.com', password='password123')
        # Minimal valid 1x1 pixel GIF
        gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        img1 = SimpleUploadedFile("i1.jpg", gif, content_type="image/jpeg")
        img2 = SimpleUploadedFile("i2.jpg", gif, content_type="image/jpeg")
        img3 = SimpleUploadedFile("i3.jpg", gif, content_type="image/jpeg")
        
        response = self.client.post(reverse('add_product'), {
            'name': 'New Product',
            'category': self.category.id,
            'description': 'Description must be at least 12 characters long.',
            'ingredients': 'Some ingredients',
            'how_to_use': 'Usage steps',
            'skin_type': 'Dry',
            'primary_index': 1,
            'images': [img1, img2, img3]
        })
        # Note: add_product view returns JSON or redirect depending on how it's called
        self.assertEqual(response.status_code, 302)
        new_p = Product.objects.get(name='New Product')
        self.assertEqual(new_p.images.count(), 3)
        self.assertTrue(new_p.images.filter(is_primary=True).exists())

    def test_variant_management_views(self):
        self.client.login(email='admin@example.com', password='password123')
        # View list
        response = self.client.get(reverse('variant_management', args=[self.product.id]))
        self.assertEqual(response.status_code, 200)
        # Add variant
        response = self.client.post(reverse('add_variant', args=[self.product.id]), {
            'size': '50ml',
            'price': 150.00,
            'stock': 100,
            'is_active': 'on'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Variant.objects.filter(product=self.product, size='50ml').exists())
