from django.test import TestCase
from django.urls import reverse



class GetPagesTestCase(TestCase):

    def test_index_page(self):
        path = reverse('main:index')
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertIn('index/index.html', response.template_name)