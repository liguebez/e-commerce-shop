from unittest.mock import patch
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class RegisterTest(TestCase):
    def test_valid_form_creates_user(self):
        with patch('captcha.fields.CaptchaField.clean', return_value='passed'):
            response = self.client.post(reverse('users:register'), {
                'username': 'newuser',
                'first_name': 'New',
                'last_name': 'User',
                'email': 'new@example.com',
                'password': 'securepass123',
                'password2': 'securepass123',
                'captcha_0': 'dummy',
                'captcha_1': 'dummy',
            })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/register_done.html')
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_weak_password_rejected(self):
        with patch('captcha.fields.CaptchaField.clean', return_value='passed'):
            response = self.client.post(reverse('users:register'), {
                'username': 'weakpwuser',
                'first_name': 'Weak',
                'last_name': 'Password',
                'email': 'weakpw@example.com',
                'password': 'password',
                'password2': 'password',
                'captcha_0': 'dummy',
                'captcha_1': 'dummy',
            })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/register.html')
        self.assertFormError(response.context['form'], 'password2', 'This password is too common.')
        self.assertFalse(User.objects.filter(username='weakpwuser').exists())

    def test_missing_captcha_rejected(self):
        response = self.client.post(reverse('users:register'), {
            'username': 'nocaptchauser',
            'first_name': 'No',
            'last_name': 'Captcha',
            'email': 'nocaptcha@example.com',
            'password': 'securepass123',
            'password2': 'securepass123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/register.html')
        self.assertFormError(response.context['form'], 'captcha', 'This field is required.')
        self.assertFalse(User.objects.filter(username='nocaptchauser').exists())


class EmailUniquenessTest(TestCase):
    def test_duplicate_email_raises_integrity_error(self):
        User.objects.create_user(username='dupe1', email='dupe@example.com', password='pass')
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(username='dupe2', email='dupe@example.com', password='pass')

    def test_case_insensitive_duplicate_rejected_by_form(self):
        User.objects.create_user(username='caseuser', email='Case@Example.com', password='pass')
        with patch('captcha.fields.CaptchaField.clean', return_value='passed'):
            response = self.client.post(reverse('users:register'), {
                'username': 'caseuser2',
                'first_name': 'Case',
                'last_name': 'Insensitive',
                'email': 'case@example.com',
                'password': 'securepass123',
                'password2': 'securepass123',
                'captcha_0': 'dummy',
                'captcha_1': 'dummy',
            })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/register.html')
        self.assertFormError(response.context['form'], 'email', 'This email already exists')
        self.assertFalse(User.objects.filter(username='caseuser2').exists())

    def test_race_condition_duplicate_email_handled_gracefully(self):
        User.objects.create_user(username='raceuser1', email='race@example.com', password='pass')
        with patch('captcha.fields.CaptchaField.clean', return_value='passed'), \
             patch('users.forms.RegisterUserForm.clean_email', return_value='race@example.com'):
            response = self.client.post(reverse('users:register'), {
                'username': 'raceuser2',
                'first_name': 'Race',
                'last_name': 'Condition',
                'email': 'race@example.com',
                'password': 'securepass123',
                'password2': 'securepass123',
                'captcha_0': 'dummy',
                'captcha_1': 'dummy',
            })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/register.html')
        self.assertFormError(response.context['form'], 'email', 'This email already exists')
        self.assertEqual(User.objects.filter(email__iexact='race@example.com').count(), 1)


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
        self.client.force_login(self.user)

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
        self.client.force_login(self.user)

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
