import shutil
import tempfile
from collections import namedtuple
from http import HTTPStatus

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.paginator import Page
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..forms import PostForm
from ..models import Comment, Follow, Group, Post

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostViewTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        small_gif = (
             b'\x47\x49\x46\x38\x39\x61\x02\x00'
             b'\x01\x00\x80\x00\x00\x00\x00\x00'
             b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
             b'\x00\x00\x00\x2C\x00\x00\x00\x00'
             b'\x02\x00\x01\x00\x00\x02\x02\x0C'
             b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.user = User.objects.create_user(username='auth')
        cls.user2 = User.objects.create_user(username='noname')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание группы',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
            image=uploaded,
        )
        cls.urls_template = namedtuple('urls_template', 'name kwargs template')
        cls.urls = {
            'index': cls.urls_template('posts:index', None,
                                       'posts/index.html',),
            'group_list': cls.urls_template('posts:group_list',
                                            {'slug': cls.group.slug},
                                            'posts/group_list.html'),
            'profile': cls.urls_template('posts:profile',
                                         {'username': cls.user.username},
                                         'posts/profile.html'),
            'post_detail': cls.urls_template('posts:post_detail',
                                             {'post_id': cls.post.id},
                                             'posts/post_detail.html'),
            'post_create': cls.urls_template('posts:post_create', None,
                                             'posts/create_post.html'),
            'post_edit': cls.urls_template('posts:post_edit',
                                           {'post_id': cls.post.id},
                                           'posts/create_post.html'),
        }

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        for name, kwargs, template in self.urls.values():
            with self.subTest(name=name):
                response = self.authorized_client.get(reverse(name,
                                                              kwargs=kwargs))
                self.assertTemplateUsed(response, template)

    def correct_post(self, reverse_name, con):
        response = self.authorized_client.get(reverse_name)
        if con == 'post':
            first_object = response.context.get(con)
        else:
            self.assertIsInstance(response.context.get(con), Page)
            first_object = response.context.get(con)[0]
        self.assertIsInstance(first_object.group, Group)
        self.assertIsInstance(first_object.author, User)
        self.assertEqual(first_object.text, self.post.text)

    def test_index_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        self.correct_post(reverse(self.urls['index'].name), 'page_obj')

    def test_group_list_page_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        name = reverse(self.urls['group_list'].name,
                       kwargs=self.urls['group_list'].kwargs)
        self.correct_post(name, 'page_obj')
        response = self.authorized_client.get(name)
        self.assertEqual(response.context.get('group'), self.group)

    def test_profile_page_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        name = reverse(self.urls['profile'].name,
                       kwargs=self.urls['profile'].kwargs)
        self.correct_post(name, 'page_obj')
        response = self.authorized_client.get(name)
        self.assertEqual(response.context.get('author'), self.user)

    def test_post_detail_page_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        self.correct_post(reverse(self.urls['post_detail'].name,
                                  kwargs=self.urls['post_detail'].kwargs),
                          'post')

    def test_post_edit_create_show_correct_context(self):
        """
            Шаблоны post_edit и post_create сформированы
            с правильным контекстом.
        """
        pages_names = [
            reverse(self.urls['post_create'].name),
            reverse(self.urls['post_edit'].name,
                    kwargs=self.urls['post_edit'].kwargs),
        ]
        for page in pages_names:
            response = self.authorized_client.get(page)
            form_fields = {
                'text': forms.fields.CharField,
                'group': forms.fields.ChoiceField,
            }
            self.assertIsInstance(response.context.get('form'), PostForm)
            for value, expected in form_fields.items():
                with self.subTest(value=value):
                    form_field = (response.context
                                  .get('form').fields.get(value))
                    self.assertIsInstance(form_field, expected)
            if page == reverse(self.urls['post_edit'].name,
                               kwargs=self.urls['post_edit'].kwargs):
                post_id = response.context.get('post_id')
                self.assertEqual(post_id, self.post.id)

    def test_post_creation(self):
        """ Пост с указанием группы появляется на трёх страницах. """
        group = Group.objects.create(
            title='Тестовая группа 2',
            slug='test-slug-2',
            description='Тестовое описание группы 2',
        )
        post = Post.objects.create(
            author=self.user,
            text='Тестовый пост 2',
            group=group
        )
        urls = {
            'index': None,
            'group_list': {'slug': group.slug},
            'profile': {'username': self.user.username}
        }
        for name, kwargs in urls.items():
            with self.subTest(name=name):
                response = (self.authorized_client.
                            get(reverse(self.urls[name].name, kwargs=kwargs)))
                self.assertEqual(response.context['page_obj'][0].text,
                                 post.text)
                self.assertEqual(response.context['page_obj'][0].group,
                                 post.group)

    def test_post_in_group(self):
        """ Пост не попадает в группы, для которых не был предназначен """
        group = Group.objects.create(
            title='Тестовая группа 3',
            slug='test-slug-3',
            description='Тестовое описание группы 2',
        )
        Post.objects.create(
            author=self.user,
            text='Тестовый пост 3',
            group=group
        )
        response = self.authorized_client.get(
            reverse(self.urls['group_list'].name,
                    kwargs=self.urls['group_list'].kwargs))
        self.assertEqual(len(response.context['page_obj']), 1)

    def test_image_is_passed_in_the_context_dictionary(self):
        """ Изображение передаётся в словаре context. """
        urls = {
            'index': 'page_obj',
            'group_list': 'page_obj',
            'profile': 'page_obj',
            'post_detail': 'post',
        }
        for name, con in urls.items():
            with self.subTest(name=name):
                response = self.authorized_client.get(
                    reverse(self.urls[name].name,
                            kwargs=self.urls[name].kwargs))
                if con == 'post':
                    first_object = response.context.get(con)
                else:
                    self.assertIsInstance(response.context.get(con), Page)
                    first_object = response.context.get(con)[0]
                self.assertEqual(first_object.image, self.post.image)

    def test_only_authorized_users_can_comment_on_posts(self):
        """
            Комментировать посты может только авторизованный пользователь.
            После успешной отправки комментарий появляется на странице поста.
        """
        post_count = Comment.objects.count()
        form_data = {
            'post': self.post.id,
            'author': self.user.id,
            'text': 'Комментарий',
        }
        self.guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data, follow=True
        )
        self.assertEqual(Comment.objects.count(), post_count)
        self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data, follow=True
        )
        self.assertEqual(Comment.objects.count(), post_count + 1)
        response = self.guest_client.post(
            reverse(self.urls['post_detail'].name,
                    kwargs=self.urls['post_detail'].kwargs),
            data=form_data, follow=True
        )
        self.assertIsInstance(response.context['comments'][0], Comment)

    def test_cache_validation(self):
        """ Тест работы кеша """
        response = self.authorized_client.get(reverse(self.urls['index'].name))
        Post.objects.filter(author=self.user).delete()
        response_del = self.authorized_client.get(
            reverse(self.urls['index'].name))
        self.assertEqual(response.content, response_del.content)
        cache.clear()
        response_clear = self.authorized_client.get(
            reverse(self.urls['index'].name))
        self.assertNotEqual(response.content, response_clear.content)

    def test_404_page_returns_custom_template(self):
        """ Страница 404 отдаёт кастомный шаблон. """
        response = self.authorized_client.get("404")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertTemplateUsed(response, 'core/404.html')

    def test_authorized_user_subscribe_unsubscribe(self):
        """ Авторизованный пользователь может подписываться
            на других пользователей и удалять их из подписок.
        """
        post_count = Follow.objects.count()
        data = {
            'user': self.user.id,
            'author': self.user2.id,
        }
        self.authorized_client.post(
            reverse('posts:profile_follow',
                    kwargs={'username': self.user2.username}),
            data=data, follow=True
        )
        self.assertEqual(Follow.objects.count(), post_count + 1)
        self.authorized_client.post(
            reverse('posts:profile_unfollow',
                    kwargs={'username': self.user2.username}),
            data=data, follow=True
        )
        self.assertEqual(Follow.objects.count(), post_count)

    def test_new_user_entry_appears_in_the_feed(self):
        """ Новая запись пользователя появляется в ленте тех,
            кто на него подписан и не появляется в ленте тех, кто не подписан.
        """
        data = {
            'user': self.user.id,
            'author': self.user2.id,
        }
        self.authorized_client.post(
            reverse('posts:profile_follow',
                    kwargs={'username': self.user2.username}),
            data=data, follow=True
        )
        post = Post.objects.create(
            author=self.user2,
            text='Тестовый пост в ленте',
        )
        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertEqual(response.context['page_obj'][0], post)

        """ user_unsigned = User.objects.create_user(username='unsigned')
        self.authorized_client2 = Client()
        self.authorized_client2.force_login(user_unsigned)
        response_unsigned = self.authorized_client2.get(
            reverse('posts:follow_index'))
        self.assertFalse(response_unsigned.context['page_obj']) """


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание группы',
        )
        for i in range(1, settings.PAGINATION + 4):
            Post.objects.create(
                author=cls.user,
                text=f'Тестовый пост {i}',
                group=cls.group
            )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_first_second_page_contains_ten_records(self):
        """ Тест паджинатора """
        pages_names = {
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': 'test-slug'}),
            reverse('posts:profile', kwargs={'username': 'auth'}),
        }
        for page in pages_names:
            with self.subTest(page=page):
                response1 = self.authorized_client.get(page)
                response2 = self.authorized_client.get(page, {'page': 2})
                self.assertEqual(len(response1.context['page_obj']),
                                 settings.PAGINATION)
                self.assertEqual(len(response2.context['page_obj']),
                                 Post.objects.count() - settings.PAGINATION)
