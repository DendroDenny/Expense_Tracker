from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test import override_settings
from django.contrib.auth import get_user_model


class PageTests(TestCase):
    def test_home_page_loads(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_profile_requires_login(self):
        response = self.client.get('/home/')
        self.assertRedirects(response, '/?next=/home/')

    def test_logged_in_user_sees_profile(self):
        user = get_user_model().objects.create_user(
            username='jordan',
            email='jordan@example.com',
            password='test-password-123',
            first_name='Jordan',
        )
        self.client.force_login(user)

        response = self.client.get('/home/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'jordan@example.com')
        self.assertContains(response, 'Jordan')
        self.assertContains(response, 'Edit profile')
        self.assertNotContains(response, '<details class="profile-editor" open>')

    def test_user_can_edit_own_profile(self):
        user = get_user_model().objects.create_user(
            username='jordan',
            email='old@example.com',
            password='test-password-123',
        )
        self.client.force_login(user)

        response = self.client.post('/home/', {
            'username': 'jordan-new',
            'email': 'new@example.com',
            'first_name': 'Jordan',
            'last_name': 'Taylor',
        })

        self.assertRedirects(response, '/home/')
        user.refresh_from_db()
        self.assertEqual(user.username, 'jordan-new')
        self.assertEqual(user.email, 'new@example.com')
        self.assertEqual(user.first_name, 'Jordan')
        self.assertEqual(user.last_name, 'Taylor')

    def test_profile_edit_rejects_an_existing_username(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            username='jordan',
            password='test-password-123',
        )
        user_model.objects.create_user(
            username='already-taken',
            password='test-password-123',
        )
        self.client.force_login(user)

        response = self.client.post('/home/', {
            'username': 'already-taken',
            'email': 'new@example.com',
            'first_name': 'Jordan',
            'last_name': 'Taylor',
        })

        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.username, 'jordan')
        self.assertContains(response, 'already exists')

    def test_user_can_upload_profile_picture(self):
        user = get_user_model().objects.create_user(
            username='jordan',
            password='test-password-123',
        )
        self.client.force_login(user)
        image_buffer = BytesIO()
        Image.new('RGB', (1, 1), color='blue').save(image_buffer, format='PNG')

        with TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                response = self.client.post('/home/', {
                    'username': 'jordan',
                    'email': '',
                    'first_name': '',
                    'last_name': '',
                    'image': SimpleUploadedFile(
                        'avatar.png',
                        image_buffer.getvalue(),
                        content_type='image/png',
                    ),
                })

                self.assertRedirects(response, '/home/')
                user.profile.refresh_from_db()
                self.assertTrue(user.profile.image.name.startswith('profile_pictures/'))
                self.assertTrue(Path(media_root, user.profile.image.name).is_file())

    def test_user_can_sign_in_and_sign_out(self):
        get_user_model().objects.create_user(
            username='jordan',
            password='test-password-123',
        )

        response = self.client.post('/', {
            'username': 'jordan',
            'password': 'test-password-123',
        })

        self.assertRedirects(response, '/home/')
        self.assertTrue(self.client.session.get('_auth_user_id'))
        response = self.client.post('/logout/')
        self.assertRedirects(response, '/')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_registration_page_loads(self):
        response = self.client.get('/register/')
        self.assertEqual(response.status_code, 200)
