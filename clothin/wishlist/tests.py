from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from main.models import Category, Product
from wishlist.models import WishlistItem


class WishlistRequiresLoginTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cat = Category.objects.create(name="Shirts", slug="shirts")
        cls.product = Product.objects.create(name="Tee", slug="tee", category=cls.cat, price=10)

    def test_add_redirects_to_login(self):
        response = self.client.post(reverse('wishlist:wishlist_add', args=[self.product.id]))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/users/login/', response.url)


class WishlistAddTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cat = Category.objects.create(name="Shirts", slug="shirts")
        cls.product = Product.objects.create(name="Tee", slug="tee", category=cls.cat, price=10)
        cls.unavailable_product = Product.objects.create(name="unavailable product", slug="unavailable-product",
                                              category=cls.cat, price=10, available=False)
        cls.user = User.objects.create_user(username="testuser", password="pass")

    def setUp(self):
        self.client.force_login(self.user)

    def test_add_creates_wishlist_item(self):
        self.client.post(reverse('wishlist:wishlist_add', args=[self.product.id]))
        self.assertTrue(WishlistItem.objects.filter(user=self.user, product=self.product).exists())
    
    def test_add_unavailable_product_to_wishlist_return_404(self):

        path = reverse('wishlist:wishlist_add', args=[self.unavailable_product.id])
        response = self.client.post(path)

        self.assertFalse(WishlistItem.objects.filter(user=self.user, product=self.unavailable_product).exists())
        self.assertEqual(response.status_code, 404)


class WishlistRemoveTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cat = Category.objects.create(name="Shirts", slug="shirts")
        cls.product = Product.objects.create(name="Tee", slug="tee", category=cls.cat, price=10)
        cls.user = User.objects.create_user(username="testuser", password="pass")

    def setUp(self):
        self.client.force_login(self.user)
        WishlistItem.objects.create(user=self.user, product=self.product)

    def test_remove_deletes_wishlist_item(self):
        self.client.post(reverse('wishlist:wishlist_remove', args=[self.product.id]))
        self.assertFalse(WishlistItem.objects.filter(user=self.user, product=self.product).exists())
