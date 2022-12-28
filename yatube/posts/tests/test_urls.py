from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Group, Post

User = get_user_model()


class PostUrlsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_auth = User.objects.create_user(username='auth')
        cls.user_noname = User.objects.create_user(username='HasNoName')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user_auth,
            text='Большой тестовый пост',
        )
        cls.public_pages = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list',
                    kwargs={'slug': cls.group.slug}): 'posts/group_list.html',
            reverse('posts:profile',
                    kwargs={'username':
                            cls.user_auth.username}): 'posts/profile.html',
            reverse('posts:post_detail',
                    kwargs={'post_id': cls.post.id}): 'posts/post_detail.html',
        }
        cls.authorized_pages = {
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit',
                    kwargs={'post_id': cls.post.id}): 'posts/create_post.html',
        }

    def setUp(self):
        self.guest_client = Client()
        self.author_client = Client()
        self.author_client.force_login(self.user_auth)
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user_noname)

    def test_public_pages(self):
        for address in self.public_pages:
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_authorized_pages(self):
        for url in self.authorized_pages:
            with self.subTest(url=url):
                response = self.author_client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_uses_correct_template(self):
        templates_url_names = {}
        templates_url_names.update(self.authorized_pages)
        templates_url_names.update(self.public_pages)
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.author_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_redirect_when_editing_someone_else_is_post(self):
        """
            Авторизованного пользователя редиректит
            при попытке редактирования чужого поста.
        """
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}))
        self.assertRedirects(response,
                             reverse('posts:post_detail',
                                     kwargs={'post_id': self.post.id}))

    def test_unauthorized_user_is_redirected_from_private_pages(self):
        """ Неавторизованного пользователя редиректит с приватных страниц. """
        for name in self.authorized_pages:
            response = self.guest_client.get(name)
            self.assertRedirects(response,
                                 reverse('users:login') + f'?next={name}')

    def test_page_404(self):
        response = self.guest_client.get('unexisting_page')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
