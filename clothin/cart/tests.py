from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from main.models import Category, Product
from cart.models import CartItem

from django.core.cache import cache
from django.test import override_settings


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
        self.client.force_login(self.user)

    def test_add_creates_cart_item(self):
        self.client.post(reverse('cart:cart_add', args=[self.product.id]), {'action': 'increment'})
        self.assertTrue(CartItem.objects.filter(user=self.user, product=self.product).exists())
    
    def test_quantity_gte_stock(self):
        low_stock_product = Product.objects.create(
            name="Rare", slug="rare", category=self.cat, price=10, stock=1
        )
        self.client.post(reverse('cart:cart_add', args=[low_stock_product.id]), {'action': 'increment'})
        response = self.client.post(reverse('cart:cart_add', args=[low_stock_product.id]), {'action': 'increment'})
        item = CartItem.objects.get(user=self.user, product=low_stock_product)
        self.assertEqual(item.quantity, 1)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('cart:cart_detail'))
    
    def test_add_zero_stock_product(self):
        zero_stock_product = Product.objects.create(name="Zero", slug='zero', category=self.cat,
                                                        price=10, stock=0, available=True)
        response = self.client.post(reverse('cart:cart_add', args=[zero_stock_product.id]), {'action': 'increment'})
        self.assertFalse(CartItem.objects.filter(user=self.user, product=zero_stock_product).exists())
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'Only 0 units available.')
        


class CartUpdateTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cat = Category.objects.create(name="Shirts", slug="shirts")
        cls.product = Product.objects.create(name="Tee", slug="tee", category=cls.cat, price=10, stock=5)
        cls.user = User.objects.create_user(username="testuser", password="pass")

    def setUp(self):
        self.client.force_login(self.user)
        CartItem.objects.create(user=self.user, product=self.product, quantity=1)

    def test_update_changes_quantity(self):
        self.client.post(reverse('cart:cart_update', args=[self.product.id]), {'quantity': 3})
        item = CartItem.objects.get(user=self.user, product=self.product)
        self.assertEqual(item.quantity, 3)
    
    def test_quantity_gte_stock(self):
        response = self.client.post(reverse('cart:cart_update', args=[self.product.id]), {'quantity': 6})
        item = CartItem.objects.get(user=self.user, product=self.product)
        self.assertEqual(item.quantity, 1)  # unchanged — save() was skipped since 6 > stock (5)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('cart:cart_detail'))


class CartRemoveTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cat = Category.objects.create(name="Shirts", slug="shirts")
        cls.product = Product.objects.create(name="Tee", slug="tee", category=cls.cat, price=10, stock=5)
        cls.user = User.objects.create_user(username="testuser", password="pass")

    def setUp(self):
        self.client.force_login(self.user)
        CartItem.objects.create(user=self.user, product=self.product, quantity=1)

    def test_remove_deletes_cart_item(self):
        self.client.post(reverse('cart:cart_remove', args=[self.product.id]))
        self.assertFalse(CartItem.objects.filter(user=self.user, product=self.product).exists())

@override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
class CartCacheInvalidationTest(TestCase):
    
    @classmethod
    def setUpTestData(cls):
        cls.cat = Category.objects.create(name="Shirts", slug="shirts")
        cls.product = Product.objects.create(name="Tee", slug="tee", category=cls.cat, price=10, stock=5)
        cls.user = User.objects.create_user(username="testuser", password="pass")

    def setUp(self):
        cache.clear()
        self.client.force_login(self.user)
        CartItem.objects.create(user=self.user, product=self.product, quantity=1)
    
    def test_add_cartitem_invalidates_cart_count_cache(self):
        cache.set(f'cart:v1:totals:user:{self.user.id}', ['stale'], 300)
        self.client.post(reverse('cart:cart_add', args=[self.product.id]), {'action': 'increment'})
        self.assertIsNone(cache.get(f'cart:v1:totals:user:{self.user.id}'))

    def test_remove_cartitem_invalidates_cart_count_cache(self):
        cache.set(f'cart:v1:totals:user:{self.user.id}', ['stale'], 300)
        self.client.post(reverse('cart:cart_remove', args=[self.product.id]))
        self.assertIsNone(cache.get(f'cart:v1:totals:user:{self.user.id}'))
        

