from django.test import TestCase, Client
from django.urls import reverse
from .models import Category
from django.contrib.auth import get_user_model

User = get_user_model()

class CategoryTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(
            username='admin@example.com',
            email='admin@example.com',
            password='password123'
        )
        self.client.login(email='admin@example.com', password='password123')
        self.category = Category.objects.create(name="Serums", is_active=True)
        self.mgmt_url = reverse('category_management')

    def test_category_creation(self):
        self.assertEqual(self.category.name, "Serums")
        self.assertTrue(self.category.is_active)
        self.assertFalse(self.category.is_deleted)

    def test_add_category_view(self):
        response = self.client.post(reverse('add_category'), {
            'name': 'Moisturizers'
        })
        self.assertRedirects(response, self.mgmt_url)
        self.assertTrue(Category.objects.filter(name='Moisturizers').exists())

    def test_edit_category_view(self):
        response = self.client.post(reverse('edit_category', args=[self.category.id]), {
            'name': 'Active Serums'
        })
        self.assertRedirects(response, self.mgmt_url)
        self.category.refresh_from_db()
        self.assertEqual(self.category.name, 'Active Serums')

    def test_toggle_category_status(self):
        response = self.client.post(reverse('toggle_category', args=[self.category.id]))
        self.assertRedirects(response, self.mgmt_url)
        self.category.refresh_from_db()
        self.assertFalse(self.category.is_active)

    def test_soft_delete_category(self):
        response = self.client.post(reverse('soft_delete_category', args=[self.category.id]))
        self.assertRedirects(response, self.mgmt_url)
        self.category.refresh_from_db()
        self.assertTrue(self.category.is_deleted)

    def test_restore_category(self):
        self.category.is_deleted = True
        self.category.save()
        response = self.client.post(reverse('restore_category', args=[self.category.id]))
        self.assertRedirects(response, self.mgmt_url)
        self.category.refresh_from_db()
        self.assertFalse(self.category.is_deleted)

    def test_permanent_delete_category(self):
        self.category.is_deleted = True
        self.category.save()
        response = self.client.post(reverse('permanent_delete_category', args=[self.category.id]))
        self.assertRedirects(response, self.mgmt_url)
        self.assertFalse(Category.objects.filter(id=self.category.id).exists())
