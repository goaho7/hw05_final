from http import HTTPStatus

from django.test import Client, TestCase


class AboutUrlsTest(TestCase):
    def setUp(self):
        self.guest_client = Client()

    def test_public_pages(self):
        url_names = [
            '/about/author/',
            '/about/tech/',
        ]
        for address in url_names:
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_uses_correct_template(self):
        templates_url_names = {
            '/about/author/': 'about/author.html',
            '/about/tech/': 'about/tech.html',
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertTemplateUsed(response, template)
