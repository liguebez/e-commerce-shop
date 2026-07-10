from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class RegisterTest(TestCase):
    def test_valid_form_creates_user(self):
        response = self.client.post(reverse('users:register'), {
            'username': 'newuser',
            'first_name': 'New',
            'last_name': 'User',
            'email': 'new@example.com',
            'password': 'securepass123',
            'password2': 'securepass123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/register_done.html')
        self.assertTrue(User.objects.filter(username='newuser').exists())


class LoginUsernameTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='testuser', password='pass')

    def test_login_with_username_redirects(self):
        response = self.client.post(reverse('users:login'), {
            'username': 'testuser',
            'password': 'pass',
        })
        self.assertRedirects(response, reverse('main:index'))


class LoginEmailTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='testuser', email='test@example.com', password='pass')

    def test_login_with_email_redirects(self):
        response = self.client.post(reverse('users:login'), {
            'username': 'test@example.com',
            'password': 'pass',
        })
        self.assertRedirects(response, reverse('main:index'))


class ProfileUpdateTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='testuser', email='testuser@example.com', password='pass')

    def setUp(self):
        self.client.login(username='testuser', password='pass')

    def test_post_updates_name(self):
        self.client.post(reverse('users:profile'), {
            'username': 'testuser',
            'email': '',
            'first_name': 'Updated',
            'last_name': 'Name',
        })
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Updated')
        self.assertEqual(self.user.last_name, 'Name')


class PasswordChangeTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='oldpass123')
        self.client.login(username='testuser', password='oldpass123')

    def test_valid_password_change_redirects(self):
        response = self.client.post(reverse('users:password_change'), {
            'old_password': 'oldpass123',
            'new_password1': 'newstrongpass456',
            'new_password2': 'newstrongpass456',
        })
        self.assertRedirects(response, reverse('users:password_change_done'))

class InvalidLoginTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='testuser', email='test@example.com', password='pass')

    def _assert_login_failed(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid username or password')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_invalid_username(self):
        response = self.client.post(reverse('users:login'), {
            'username': 'test2',
            'password': 'pass',
        })
        self._assert_login_failed(response)

    def test_invalid_password(self):
        response = self.client.post(reverse('users:login'), {
            'username': 'testuser',
            'password': 'pass2',
        })
        self._assert_login_failed(response)

    def test_invalid_email_wrong_password(self):
        response = self.client.post(reverse('users:login'), {
            'username': 'test@example.com',  # real email, wrong password
            'password': 'wrongpass',
        })
        self._assert_login_failed(response)
