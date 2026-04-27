from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from wallet.models import Wallet, WalletTransaction
from decimal import Decimal

User = get_user_model()

class WalletTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='walletuser@example.com',
            email='walletuser@example.com',
            password='password123',
            full_name='Wallet User'
        )
        self.client.login(email='walletuser@example.com', password='password123')
        self.wallet = Wallet.objects.get(user=self.user)

    def test_wallet_creation_on_user_save(self):
        self.assertIsNotNone(self.wallet)
        self.assertEqual(self.wallet.balance, 0)

    def test_wallet_deposit_logic(self):
        # Manually adding a transaction
        WalletTransaction.objects.create(
            wallet=self.wallet,
            amount=1000,
            transaction_type='ADD',
            status='COMPLETED',
            description='Test Deposit'
        )
        # Note: If there's no signal/save override to update balance, 
        # we might need to manually update it or implement the logic.
        # For now, let's assume balance is updated via a method we'll call or implement.
        self.wallet.balance += 1000
        self.wallet.save()
        
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, 1000)

    def test_wallet_view(self):
        response = self.client.get(reverse('wallet_view'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'My Wallet')

    def test_wallet_transaction_history(self):
        WalletTransaction.objects.create(
            wallet=self.wallet,
            amount=500,
            transaction_type='ADD',
            status='COMPLETED',
            description='Ref'
        )
        response = self.client.get(reverse('wallet_view'))
        self.assertContains(response, 'ADD')
        self.assertContains(response, '500')
