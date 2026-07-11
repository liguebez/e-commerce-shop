import stripe
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from main.models import Category, Product
from orders.models import Order, OrderItem

User = get_user_model()


class WebhookInvalidSignatureTest(TestCase):
    def test_bad_signature_returns_400(self):
        with patch('stripe.Webhook.construct_event',
                   side_effect=stripe.error.SignatureVerificationError('bad sig', 'sig_header')):
            response = self.client.post(
                reverse('payment:payment_webhook'),
                data='{}',
                content_type='application/json',
                HTTP_STRIPE_SIGNATURE='bad_sig',
            )
        self.assertEqual(response.status_code, 400)


class WebhookValidEventTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cat = Category.objects.create(name="Shirts", slug="shirts")
        cls.product = Product.objects.create(name="Tee", slug="tee", category=cls.cat, price=10, stock=5)
        cls.user = User.objects.create_user(username="testuser", password="pass")

    def setUp(self):
        self.order = Order.objects.create(
            user=self.user,
            first_name="Test", last_name="User", email="test@example.com",
            address="123 St", postal_code="12345", city="City",
        )
        OrderItem.objects.create(
            orders=self.order,
            product=self.product,
            price=self.product.get_price(),
            quantity=1,
        )

    def _make_event(self):
        mock_session = MagicMock()
        mock_session.mode = 'payment'
        mock_session.payment_status = 'paid'
        mock_session.client_reference_id = self.order.id
        mock_session.payment_intent = 'pi_test_123'
        mock_event = MagicMock()
        mock_event.type = 'checkout.session.completed'
        mock_event.data.object = mock_session
        return mock_event

    def test_valid_event_sets_order_paid(self):
        with patch('stripe.Webhook.construct_event', return_value=self._make_event()), \
             patch('django.core.mail.send_mail'):
            response = self.client.post(
                reverse('payment:payment_webhook'),
                data='{}',
                content_type='application/json',
                HTTP_STRIPE_SIGNATURE='sig',
            )
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertTrue(self.order.paid)

    def test_missing_order_returns_400(self):
        mock_session = MagicMock()
        mock_session.mode = 'payment'
        mock_session.payment_status = 'paid'
        mock_session.client_reference_id = 999999
        mock_session.payment_intent = 'pi_test_missing'
        mock_event = MagicMock()
        mock_event.type = 'checkout.session.completed'
        mock_event.data.object = mock_session
        with patch('stripe.Webhook.construct_event', return_value=mock_event):
            response = self.client.post(
                reverse('payment:payment_webhook'),
                data='{}',
                content_type='application/json',
                HTTP_STRIPE_SIGNATURE='sig',
            )
        self.assertEqual(response.status_code, 400)

    def test_duplicate_completed_event_does_not_touch_stock(self):
        # Stock is now reserved at order-creation time (orders/views.py), not
        # decremented again here, so the completed webhook must never change
        # it -- duplicate delivery included.
        with patch('stripe.Webhook.construct_event', return_value=self._make_event()), \
             patch('django.core.mail.send_mail'):
            for _ in range(2):
                response = self.client.post(
                    reverse('payment:payment_webhook'),
                    data='{}',
                    content_type='application/json',
                    HTTP_STRIPE_SIGNATURE='sig',
                )
                self.assertEqual(response.status_code, 200)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)


class PaymentProcessOwnershipTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_a = User.objects.create_user(username="usera", password="pass")
        cls.user_b = User.objects.create_user(username="userb", password="pass")

    def setUp(self):
        self.order_b = Order.objects.create(
            user=self.user_b,
            first_name="User", last_name="B", email="userb@example.com",
            address="456 St", postal_code="54321", city="City",
        )

    def test_cannot_view_another_users_order_via_stale_session(self):
        self.client.force_login(self.user_a)
        session = self.client.session
        session['order_id'] = self.order_b.id
        session.save()

        response = self.client.get(reverse('payment:payment_process'))

        self.assertEqual(response.status_code, 404)


class WebhookExpiredEventTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cat = Category.objects.create(name="Shirts", slug="shirts")
        # Stock already reserved (decremented from 5 to 4) at order-creation time.
        cls.product = Product.objects.create(name="Tee", slug="tee", category=cls.cat, price=10, stock=4)
        cls.user = User.objects.create_user(username="testuser", password="pass")

    def setUp(self):
        self.order = Order.objects.create(
            user=self.user,
            first_name="Test", last_name="User", email="test@example.com",
            address="123 St", postal_code="12345", city="City",
        )
        OrderItem.objects.create(
            orders=self.order,
            product=self.product,
            price=self.product.get_price(),
            quantity=1,
        )

    def _make_expired_event(self):
        mock_session = MagicMock()
        mock_session.client_reference_id = self.order.id
        mock_event = MagicMock()
        mock_event.type = 'checkout.session.expired'
        mock_event.data.object = mock_session
        return mock_event

    def test_expired_event_deletes_unpaid_order_and_restores_stock(self):
        with patch('stripe.Webhook.construct_event', return_value=self._make_expired_event()):
            response = self.client.post(
                reverse('payment:payment_webhook'),
                data='{}',
                content_type='application/json',
                HTTP_STRIPE_SIGNATURE='sig',
            )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Order.objects.filter(id=self.order.id).exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)
