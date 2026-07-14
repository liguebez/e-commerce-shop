from unittest.mock import patch
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Category, Product
from django.core.cache import cache
from django.test import override_settings



class GetPagesTestCase(TestCase):

    def test_index_page(self):
        path = reverse('main:index')
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'index/index.html')

class ProductListTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cat = Category.objects.create(name="Shirts", slug="shirts")
        cls.product = Product.objects.create(name="Blue shirt", slug='blue-shirt', category=cls.cat, price=20)
    
    def test_return_200(self):
        path = reverse('main:product_list')
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
    
    def test_products_in_context(self):
        path = reverse('main:product_list')
        response = self.client.get(path)
        self.assertIn(self.product, response.context["current_page"].object_list)

class CategoryFilterTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.shirts = Category.objects.create(name="Shirts", slug='shirts')
        cls.pants = Category.objects.create(name="Pants", slug='pants')
        cls.shirt = Product.objects.create(name="Tee", slug='tee', category=cls.shirts, price=10)
        cls.pant = Product.objects.create(name="Jeans", slug='jeans', category=cls.pants, price=10)


    def test_filter_by_category(self):
        path = reverse('main:product_list_by_category', args=['shirts'])
        response = self.client.get(path)
        self.assertIn(self.shirt, response.context["current_page"].object_list)
        self.assertNotIn(self.pant, response.context["current_page"].object_list)
    
class ProductDetailTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.cat = Category.objects.create(name="Shirts", slug="shirts")
        cls.product = Product.objects.create(name="Blue shirt", slug='blue-shirt', category=cls.cat, price=20)
        cls.unavailable_product = Product.objects.create(name="unavailable product", slug='unavailable-product',
                                                         category=cls.cat, price=20, available=False)

    def test_return_200_with_correct_product(self):
        path = reverse('main:product_detail', args=['shirts', 'blue-shirt'])
        response = self.client.get(path)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.product, response.context['product'])
        self.assertEqual(self.cat, response.context['category'])
    
    def test_get_unavailable_product_return_404(self):
        path = reverse('main:product_detail', args=['shirts', 'unavailable-product'])
        response = self.client.get(path)

        self.assertEqual(response.status_code, 404)


class ContactFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='pass')
        self.client.force_login(self.user)

    def test_valid_form_redirects(self):
        with patch('captcha.fields.CaptchaField.clean', return_value='passed'):
            response = self.client.post(reverse('main:contact'), {
                'name': 'Test User',
                'email': 'test@example.com',
                'content': 'Hello there',
                'captcha_0': 'dummy',
                'captcha_1': 'dummy',
            })
        self.assertRedirects(response, reverse('main:contact'))

    def test_missing_fields_show_errors(self):
        with patch('captcha.fields.CaptchaField.clean', return_value='passed'):
            response = self.client.post(reverse('main:contact'), {
                'captcha_0': 'dummy',
                'captcha_1': 'dummy',
            })
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertFormError(form, 'name', 'This field is required.')
        self.assertFormError(form, 'email', 'This field is required.')
        self.assertFormError(form, 'content', 'This field is required.')

    def test_name_with_embedded_newline_does_not_break_subject(self):
        with patch('captcha.fields.CaptchaField.clean', return_value='passed'):
            response = self.client.post(reverse('main:contact'), {
                'name': 'Evil\r\nBcc: attacker@evil.com',
                'email': 'test@example.com',
                'content': 'Hello there',
                'captcha_0': 'dummy',
                'captcha_1': 'dummy',
            })
        self.assertRedirects(response, reverse('main:contact'))
        self.assertEqual(len(mail.outbox), 1)
        subject = mail.outbox[0].subject
        self.assertNotIn('\n', subject)
        self.assertNotIn('\r', subject)
        self.assertEqual(subject, 'Contact form: message from Evil  Bcc: attacker@evil.com')


class SearchTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cat = Category.objects.create(name="Shirts", slug="shirts")
        cls.match = Product.objects.create(name="Blue Shirt", slug='blue-shirt', category=cls.cat, price=20)
        cls.no_match = Product.objects.create(name="Black Jeans", slug='black-jeans', category=cls.cat, price=30)

    def test_returns_only_matching_products(self):
        response = self.client.get(reverse('main:product_list'), {'q': 'shirt'})
        self.assertEqual(response.status_code, 200)
        results = response.context['current_page'].object_list
        self.assertIn(self.match, results)
        self.assertNotIn(self.no_match, results)


@override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
class CacheInvalidationTest(TestCase):
    def setUp(self):
        cache.clear()

    def test_category_save_invalidates_categories_cache(self):
        cat = Category.objects.create(name="Hats", slug="hats")
        cache.set('main:v1:categories:all', ['stale'], 300)
        cat.save()
        self.assertIsNone(cache.get('main:v1:categories:all'))

    def test_product_save_invalidates_homepage_cache(self):
        cat = Category.objects.create(name="Hats", slug="hats")
        product = Product.objects.create(name="Cap", slug="cap", category=cat, price=10)
        cache.set('main:v1:homepage_products', ['stale'], 300)
        product.save()
        self.assertIsNone(cache.get('main:v1:homepage_products'))

        