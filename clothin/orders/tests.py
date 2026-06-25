from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from main.models import Category, Product
from cart.models import CartItem
from orders.models import Order

User = get_user_model()


class OrderCreateTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cat = Category.objects.create(name="Shirts", slug="shirts")
        cls.product = Product.objects.create(name="Tee", slug="tee", category=cls.cat, price=10, stock=5)
        cls.user = User.objects.create_user(username="testuser", password="pass")

    def setUp(self):
        self.client.login(username="testuser", password="pass")
        CartItem.objects.create(user=self.user, product=self.product, quantity=1)

    def test_creates_order_and_stores_session(self):
        response = self.client.post(reverse('orders:order_create'), {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'address': '123 Main St',
            'postal_code': '12345',
            'city': 'Testville',
        })
        self.assertEqual(Order.objects.filter(user=self.user).count(), 1)
        self.assertIn('order_id', self.client.session)
        self.assertRedirects(response, reverse('payment:payment_process'), fetch_redirect_response=False)


class OrderListTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="testuser", password="pass")
        cls.other = User.objects.create_user(username="otheruser", password="pass")

    def setUp(self):
        self.order = Order.objects.create(
            user=self.user,
            first_name="Test", last_name="User", email="test@example.com",
            address="123 St", postal_code="12345", city="City",
        )
        Order.objects.create(
            user=self.other,
            first_name="Other", last_name="User", email="other@example.com",
            address="456 St", postal_code="67890", city="Town",
        )

    def test_requires_login(self):
        response = self.client.get(reverse('orders:order_list'))
        self.assertEqual(response.status_code, 302)

    def test_returns_only_user_orders(self):
        self.client.login(username="testuser", password="pass")
        response = self.client.get(reverse('orders:order_list'))
        self.assertEqual(response.status_code, 200)
        orders = list(response.context['orders'])
        self.assertIn(self.order, orders)
        self.assertEqual(len(orders), 1)
