from django.test import TestCase


class PageTests(TestCase):
    def test_home_page_loads(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_registration_page_loads(self):
        response = self.client.get('/register/')
        self.assertEqual(response.status_code, 200)
