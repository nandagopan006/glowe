from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from user.models import Address
from unittest.mock import patch

User = get_user_model()

class UserAppTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser@example.com',
            email='testuser@example.com',
            password='password123',
            full_name='Test User',
            is_verified=True,
            is_active=True
        )
        self.client.login(email='testuser@example.com', password='password123')
        
        self.address = Address.objects.create(
            user=self.user,
            label='HOME',
            full_name='Test Name',
            street_address='123 Main St',
            city='Test City',
            state='Test State',
            district='Test District',
            pincode='123456',
            phone_number='9876543210',
            is_default=True
        )

    def test_address_list_view(self):
        response = self.client.get(reverse('address'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '123 Main St')

    @patch('requests.get')
    def test_add_address(self, mock_get):
        mock_response = mock_get.return_value
        mock_response.json.return_value = [{'Status': 'Success', 'PostOffice': [{'Name': 'Office City', 'State': 'Office State', 'District': 'Office District'}]}]
        response = self.client.post(reverse('add_address'), {
            'label': 'OFFICE',
            'full_name': 'Office Name',
            'street_address': '456 Office St',
            'city': 'Office City',
            'state': 'Office State',
            'district': 'Office District',
            'pincode': '654321',
            'phone_number': '9987654321',
            'country': 'India'
        })
        self.assertRedirects(response, reverse('address'))
        self.assertEqual(Address.objects.filter(user=self.user).count(), 2)

    @patch('requests.get')
    def test_edit_address(self, mock_get):
        mock_response = mock_get.return_value
        mock_response.json.return_value = [{'Status': 'Success', 'PostOffice': [{'Name': 'Test City', 'State': 'Test State', 'District': 'Test District'}]}]
        response = self.client.post(reverse('edit_address', args=[self.address.id]), {
            'label': 'HOME',
            'full_name': 'Test Name Updated',
            'street_address': '123 Main St',
            'city': 'Test City',
            'state': 'Test State',
            'district': 'Test District',
            'pincode': '123456',
            'phone_number': '9876543210',
            'country': 'India'
        })
        if response.status_code == 200:
            print("EDIT ADDRESS FORM ERRORS:", response.context['form'].errors)
        self.assertRedirects(response, reverse('address'))
        self.address.refresh_from_db()
        self.assertEqual(self.address.full_name, 'Test Name Updated')

    def test_delete_address(self):
        # Currently the view allows GET to delete
        response = self.client.get(reverse('delete_address', args=[self.address.id]))
        self.assertRedirects(response, reverse('address'))
        self.assertEqual(Address.objects.filter(user=self.user).count(), 0)

    def test_cannot_delete_other_user_address(self):
        other_user = User.objects.create_user(
            username='other@example.com',
            email='other@example.com',
            password='password123',
            is_verified=True,
            is_active=True
        )
        other_address = Address.objects.create(
            user=other_user,
            label='HOME',
            full_name='Other',
            street_address='789 Other St',
            city='Other',
            state='Other',
            district='Other',
            pincode='111111',
            phone_number='1111111111',
            is_default=True
        )
        
        response = self.client.get(reverse('delete_address', args=[other_address.id]))
        self.assertEqual(response.status_code, 404)
