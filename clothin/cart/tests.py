from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from main.models import Category, Product
from cart.models import CartItem


class CartRequiresLoginTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cat = Category.objects.create(name="Shirts", slug="shirts")
        cls.product = Product.objects.create(name="Tee", slug="tee", category=cls.cat, price=10, stock=5)

    def test_add_redirects_to_login(self):
        response = self.client.post(reverse('cart:cart_add', args=[self.product.id]), {'action': 'increment'})
        self.assertEqual(response.status_code, 302)
        self.assertIn('/users/login/', response.url)


class CartAddTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cat = Category.objects.create(name="Shirts", slug="shirts")
        cls.product = Product.objects.create(name="Tee", slug="tee", category=cls.cat, price=10, stock=5)
        cls.user = User.objects.create_user(username="testuser", password="pass")

    def setUp(self):
        self.client.login(username="testuser", password="pass")

    def test_add_creates_cart_item(self):
        self.client.post(reverse('cart:cart_add', args=[self.product.id]), {'action': 'increment'})
        self.assertTrue(CartItem.objects.filter(user=self.user, product=self.product).exists())


class CartUpdateTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cat = Category.objects.create(name="Shirts", slug="shirts")
        cls.product = Product.objects.create(name="Tee", slug="tee", category=cls.cat, price=10, stock=5)
        cls.user = User.objects.create_user(username="testuser", password="pass")

    def setUp(self):
        self.client.login(username="testuser", password="pass")
        CartItem.objects.create(user=self.user, product=self.product, quantity=1)

    def test_update_changes_quantity(self):
        self.client.post(reverse('cart:cart_update', args=[self.product.id]), {'quantity': 3})
        item = CartItem.objects.get(user=self.user, product=self.product)
        self.assertEqual(item.quantity, 3)


class CartRemoveTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cat = Category.objects.create(name="Shirts", slug="shirts")
        cls.product = Product.objects.create(name="Tee", slug="tee", category=cls.cat, price=10, stock=5)
        cls.user = User.objects.create_user(username="testuser", password="pass")

    def setUp(self):
        self.client.login(username="testuser", password="pass")
        CartItem.objects.create(user=self.user, product=self.product, quantity=1)

    def test_remove_deletes_cart_item(self):
        self.client.post(reverse('cart:cart_remove', args=[self.product.id]))
        self.assertFalse(CartItem.objects.filter(user=self.user, product=self.product).exists())
