from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from main.models import Category, Product
from cart.models import CartItem
from orders.models import Order, OrderItem

User = get_user_model()


class OrderCreateTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cat = Category.objects.create(name="Shirts", slug="shirts")
        cls.product = Product.objects.create(name="Tee", slug="tee", category=cls.cat, price=10, stock=5)
        cls.user = User.objects.create_user(username="testuser", password="pass")

    def setUp(self):
        self.client.force_login(self.user)
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

    def test_creates_order_reserves_stock(self):
        self.client.post(reverse('orders:order_create'), {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'address': '123 Main St',
            'postal_code': '12345',
            'city': 'Testville',
        })
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 4)  # 5 - 1, reserved immediately

    def test_second_buyer_rejected_once_stock_is_reserved(self):
        other = User.objects.create_user(username="otherbuyer", password="pass")
        self.product.stock = 1
        self.product.save()

        # First buyer takes the last unit.
        self.client.post(reverse('orders:order_create'), {
            'first_name': 'First',
            'last_name': 'Buyer',
            'email': 'first@example.com',
            'address': '123 Main St',
            'postal_code': '12345',
            'city': 'Testville',
        })
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 0)

        # Second buyer's cart still references the product; their order
        # creation must now be rejected instead of oversold.
        self.client.logout()
        self.client.force_login(other)
        CartItem.objects.create(user=other, product=self.product, quantity=1)
        response = self.client.post(reverse('orders:order_create'), {
            'first_name': 'Second',
            'last_name': 'Buyer',
            'email': 'second@example.com',
            'address': '456 Main St',
            'postal_code': '54321',
            'city': 'Testville',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('cart:cart_detail'))
        self.assertEqual(Order.objects.filter(user=other).count(), 0)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 0)
    
    def test_creates_order_deletes_cart(self):
        other_product = Product.objects.create(name="Cap", slug="cap", category=self.cat, price=15, stock=5)
        CartItem.objects.create(user=self.user, product=other_product, quantity=1)

        self.client.post(reverse('orders:order_create'), {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'address': '123 Main St',
            'postal_code': '12345',
            'city': 'Testville',
        })

        self.assertEqual(Order.objects.filter(user=self.user).count(), 1)
        self.assertFalse(CartItem.objects.filter(user=self.user).exists())

    def test_resubmitting_with_empty_cart_does_not_create_order(self):
        post_data = {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'address': '123 Main St',
            'postal_code': '12345',
            'city': 'Testville',
        }
        self.client.post(reverse('orders:order_create'), post_data)
        self.assertEqual(Order.objects.filter(user=self.user).count(), 1)

        response = self.client.post(reverse('orders:order_create'), post_data)
        self.assertEqual(Order.objects.filter(user=self.user).count(), 1)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('cart:cart_detail'))


class OrderCreateInvalidPostTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='testuser', password='pass')

    def setUp(self):
        self.client.force_login(self.user)

    def test_invalid_rerenders_form(self):
        response = self.client.post(reverse('orders:order_create'), {
            'first_name': 'Test',
        })

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)



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
        self.client.force_login(self.user)
        response = self.client.get(reverse('orders:order_list'))
        self.assertEqual(response.status_code, 200)
        orders = list(response.context['orders'])
        self.assertIn(self.order, orders)
        self.assertEqual(len(orders), 1)


class ReleaseExpiredOrdersCommandTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cat = Category.objects.create(name="Shirts", slug="shirts")
        cls.user = User.objects.create_user(username="testuser", password="pass")

    def _backdate(self, order, minutes):
        Order.objects.filter(id=order.id).update(
            created=timezone.now() - timezone.timedelta(minutes=minutes)
        )

    def test_releases_stale_unpaid_order_and_restores_stock(self):
        product = Product.objects.create(name="Tee", slug="tee", category=self.cat, price=10, stock=4)
        order = Order.objects.create(
            user=self.user,
            first_name="Test", last_name="User", email="test@example.com",
            address="123 St", postal_code="12345", city="City",
        )
        OrderItem.objects.create(orders=order, product=product, price=product.get_price(), quantity=1)
        self._backdate(order, minutes=31)

        call_command('release_expired_orders')

        self.assertFalse(Order.objects.filter(id=order.id).exists())
        product.refresh_from_db()
        self.assertEqual(product.stock, 5)

    def test_leaves_recent_unpaid_order_untouched(self):
        product = Product.objects.create(name="Tee", slug="tee", category=self.cat, price=10, stock=4)
        order = Order.objects.create(
            user=self.user,
            first_name="Test", last_name="User", email="test@example.com",
            address="123 St", postal_code="12345", city="City",
        )
        OrderItem.objects.create(orders=order, product=product, price=product.get_price(), quantity=1)

        call_command('release_expired_orders')

        self.assertTrue(Order.objects.filter(id=order.id).exists())
        product.refresh_from_db()
        self.assertEqual(product.stock, 4)

    def test_leaves_paid_order_untouched(self):
        product = Product.objects.create(name="Tee", slug="tee", category=self.cat, price=10, stock=4)
        order = Order.objects.create(
            user=self.user, paid=True,
            first_name="Test", last_name="User", email="test@example.com",
            address="123 St", postal_code="12345", city="City",
        )
        OrderItem.objects.create(orders=order, product=product, price=product.get_price(), quantity=1)
        self._backdate(order, minutes=31)

        call_command('release_expired_orders')

        self.assertTrue(Order.objects.filter(id=order.id).exists())
        product.refresh_from_db()
        self.assertEqual(product.stock, 4)
