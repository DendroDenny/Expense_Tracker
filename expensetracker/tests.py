from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test import override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import Expense, MonthlyBudget


class ExpenseAPITests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='api-user',
            password='test-password-123',
        )
        self.client.force_authenticate(self.user)
        self.expense_url = '/api/expenses/'

    def test_user_can_create_list_retrieve_update_and_delete_expenses(self):
        expense_date = timezone.localdate()
        payload = {
            'amount': '8000.00',
            'category': Expense.Category.FOOD,
            'date': expense_date.isoformat(),
            'note': 'Lunch',
        }

        response = self.client.post(self.expense_url, payload, format='json')
        self.assertEqual(response.status_code, 201)
        expense_id = response.data['id']
        self.assertEqual(response.data['amount'], '8000.00')
        expense = Expense.objects.get(pk=expense_id)
        self.assertEqual(expense.user, self.user)

        response = self.client.get(self.expense_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

        detail_url = f'{self.expense_url}{expense_id}/'
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['note'], 'Lunch')

        response = self.client.patch(
            detail_url,
            {'amount': '12000.00', 'note': 'Dinner'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        expense.refresh_from_db()
        self.assertEqual(expense.amount, 12000)
        self.assertEqual(expense.note, 'Dinner')

        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Expense.objects.filter(pk=expense_id).exists())

    def test_expense_api_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.expense_url)

        self.assertIn(response.status_code, (401, 403))

    def test_user_cannot_access_another_users_expenses(self):
        other_user = get_user_model().objects.create_user(
            username='other-api-user',
            password='test-password-123',
        )
        expense = Expense.objects.create(
            user=other_user,
            amount=8000,
            category=Expense.Category.FOOD,
            date=timezone.localdate(),
        )

        response = self.client.get(f'{self.expense_url}{expense.pk}/')

        self.assertEqual(response.status_code, 404)

    def test_expense_api_rejects_nonpositive_amount(self):
        response = self.client.post(self.expense_url, {
            'amount': '0',
            'category': Expense.Category.FOOD,
            'date': timezone.localdate().isoformat(),
        }, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('amount', response.data)
        self.assertFalse(Expense.objects.exists())


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
        self.assertContains(response, 'id="profile-modal"')
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
        self.assertContains(response, 'id="profile-modal" data-show-on-load')

    def test_user_can_create_edit_and_delete_expenses(self):
        user = get_user_model().objects.create_user(
            username='jordan',
            password='test-password-123',
        )
        self.client.force_login(user)
        expense_date = timezone.localdate().replace(day=9)
        post_data = {
            'action': 'expense',
            'amount': '8000',
            'category': 'food',
            'date': expense_date.isoformat(),
            'note': 'Lunch',
            'month': expense_date.strftime('%Y-%m'),
        }

        response = self.client.post('/home/', post_data)
        self.assertRedirects(response, f"/home/?month={expense_date:%Y-%m}")
        expense = Expense.objects.get(user=user)
        self.assertEqual(expense.amount, 8000)
        self.assertEqual(expense.note, 'Lunch')

        response = self.client.post('/home/', {
            **post_data,
            'expense_id': expense.pk,
            'amount': '12000',
            'note': 'Dinner',
        })
        self.assertRedirects(response, f"/home/?month={expense_date:%Y-%m}")
        expense.refresh_from_db()
        self.assertEqual(expense.amount, 12000)
        self.assertEqual(expense.note, 'Dinner')

        response = self.client.post('/home/', {
            'action': 'delete_expense',
            'expense_id': expense.pk,
            'month': expense_date.strftime('%Y-%m'),
        })
        self.assertRedirects(response, f"/home/?month={expense_date:%Y-%m}")
        self.assertFalse(Expense.objects.filter(pk=expense.pk).exists())

    def test_dashboard_summarizes_expenses_and_filters_category(self):
        user = get_user_model().objects.create_user(
            username='jordan',
            password='test-password-123',
        )
        self.client.force_login(user)
        expense_date = timezone.localdate().replace(day=9)
        Expense.objects.create(
            user=user,
            amount=8000,
            category=Expense.Category.FOOD,
            date=expense_date,
            note='Lunch',
        )
        Expense.objects.create(
            user=user,
            amount=12000,
            category=Expense.Category.TRANSPORT,
            date=expense_date,
            note='Taxi',
        )

        response = self.client.get('/home/', {
            'month': expense_date.strftime('%Y-%m'),
            'category': Expense.Category.FOOD,
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['expenses']), 1)
        self.assertEqual(response.context['total_spent'], 20000)
        self.assertEqual(response.context['monthly_budget'].amount, 300000)
        self.assertContains(response, 'Lunch')
        self.assertNotContains(response, 'Taxi')

    def test_monthly_budget_is_saved_per_user_and_month(self):
        user = get_user_model().objects.create_user(
            username='jordan',
            password='test-password-123',
        )
        self.client.force_login(user)
        target_month = timezone.localdate().replace(day=1).strftime('%Y-%m')

        response = self.client.post('/home/', {
            'action': 'budget',
            'amount': '450000',
            'month': target_month,
        })

        self.assertRedirects(response, f'/home/?month={target_month}')
        self.assertEqual(
            MonthlyBudget.objects.get(user=user).amount,
            450000,
        )

    def test_user_cannot_edit_another_users_expense(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(
            username='owner',
            password='test-password-123',
        )
        other_user = user_model.objects.create_user(
            username='other',
            password='test-password-123',
        )
        expense = Expense.objects.create(
            user=owner,
            amount=8000,
            category=Expense.Category.FOOD,
            date=timezone.localdate(),
        )
        self.client.force_login(other_user)

        response = self.client.post('/home/', {
            'action': 'expense',
            'expense_id': expense.pk,
            'amount': '1',
            'category': 'food',
            'date': timezone.localdate().isoformat(),
            'note': 'Changed',
        })

        self.assertEqual(response.status_code, 404)
        expense.refresh_from_db()
        self.assertEqual(expense.amount, 8000)

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
