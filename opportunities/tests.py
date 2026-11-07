from datetime import timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.test import TestCase, Client
from django.utils import timezone
from accounts.models import User
from .models import Opportunity
from applications.models import Application


class OpportunityModelAndF1Tests(TestCase):
    def setUp(self):
        self.client = Client()
        self.unverified_org = User.objects.create_user(
            email='new_org@nsu.ru',
            password='password123',
            name='Новый Организатор',
            role=User.Role.ORGANIZER,
            verified=False
        )
        self.verified_org = User.objects.create_user(
            email='old_org@nsu.ru',
            password='password123',
            name='Опытный Организатор',
            role=User.Role.ORGANIZER,
            verified=True,
            verified_at=timezone.now()
        )
        self.moderator = User.objects.create_superuser(
            email='mod@nsu.ru',
            password='password123',
            name='Модератор'
        )
        self.student = User.objects.create_user(
            email='student@nsu.ru',
            password='password123',
            name='Студент',
            role=User.Role.STUDENT
        )

    def test_validation_date_and_workload_bounds(self):
        now = timezone.now()
        opp = Opportunity(
            organizer=self.verified_org,
            category=Opportunity.Category.VOLUNTEER,
            title='Тестовая роль',
            duties='Обязанности',
            location='Главный корпус',
            skills='Без опыта',
            capacity=5,
            workload=Decimal('0.1'),  # Слишком мало (< 0.5)
            starts_at=now + timedelta(days=2),
            ends_at=now + timedelta(days=1),  # Окончание раньше начала!
            deadline=now + timedelta(days=3),  # Дедлайн позже начала!
            reward_types=[Opportunity.RewardType.NONE, Opportunity.RewardType.FOOD],  # 'none' с другим!
            reward_condition='Обед'
        )
        with self.assertRaises(ValidationError) as ctx:
            opp.validate_for_publication()
        errors = ctx.exception.message_dict
        self.assertIn('workload', errors)
        self.assertIn('ends_at', errors)
        self.assertIn('starts_at', errors)
        self.assertIn('reward_types', errors)

    def test_unverified_organizer_goes_to_pending_review(self):
        self.client.login(username='new_org@nsu.ru', password='password123')
        now = timezone.now()
        response = self.client.post('/organizer/cards/new/', {
            'action': 'publish',
            'category': 'one_off',
            'title': 'Первая роль нового орга',
            'duties': 'Помочь перенести коробки',
            'location': 'Ректорат',
            'workload': '2.0',
            'capacity': 3,
            'skills': 'Физическая сила',
            'deadline': (now + timedelta(days=2)).strftime('%Y-%m-%dT%H:%M'),
            'starts_at': (now + timedelta(days=3)).strftime('%Y-%m-%dT%H:%M'),
            'ends_at': (now + timedelta(days=3, hours=2)).strftime('%Y-%m-%dT%H:%M'),
            'reward_types': ['food'],
            'reward_condition': 'Пицца'
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        opp = Opportunity.objects.get(title='Первая роль нового орга')
        self.assertEqual(opp.status, Opportunity.Status.PENDING_REVIEW)
        self.assertFalse(self.unverified_org.verified)

    def test_moderator_approval_publishes_card_and_verifies_author(self):
        now = timezone.now()
        opp = Opportunity.objects.create(
            organizer=self.unverified_org,
            category=Opportunity.Category.VOLUNTEER,
            title='Роль на проверке',
            duties='Задачи',
            location='НГУ',
            skills='Любые',
            capacity=2,
            workload=Decimal('3.0'),
            deadline=now + timedelta(days=2),
            starts_at=now + timedelta(days=3),
            ends_at=now + timedelta(days=3, hours=3),
            reward_types=['merch'],
            reward_condition='Мерч',
            status=Opportunity.Status.PENDING_REVIEW
        )

        self.client.login(username='mod@nsu.ru', password='password123')
        resp = self.client.post(f'/moderation/{opp.pk}/approve/', follow=True)
        self.assertEqual(resp.status_code, 200)

        opp.refresh_from_db()
        self.assertEqual(opp.status, Opportunity.Status.PUBLISHED)
        self.assertIsNotNone(opp.published_at)

        self.unverified_org.refresh_from_db()
        self.assertTrue(self.unverified_org.verified)
        self.assertIsNotNone(self.unverified_org.verified_at)

    def test_moderator_return_with_reason(self):
        now = timezone.now()
        opp = Opportunity.objects.create(
            organizer=self.unverified_org,
            category=Opportunity.Category.VOLUNTEER,
            title='Недоработанная роль',
            duties='Задачи',
            location='НГУ',
            skills='Любые',
            capacity=2,
            workload=Decimal('3.0'),
            deadline=now + timedelta(days=2),
            starts_at=now + timedelta(days=3),
            ends_at=now + timedelta(days=3, hours=3),
            reward_types=['merch'],
            reward_condition='Мерч',
            status=Opportunity.Status.PENDING_REVIEW
        )

        self.client.login(username='mod@nsu.ru', password='password123')
        resp = self.client.post(f'/moderation/{opp.pk}/return/', {
            'moderation_note': 'Уточните аудиторию и детали смены'
        }, follow=True)
        self.assertEqual(resp.status_code, 200)

        opp.refresh_from_db()
        self.assertEqual(opp.status, Opportunity.Status.DRAFT)
        self.assertEqual(opp.moderation_note, 'Уточните аудиторию и детали смены')

        self.unverified_org.refresh_from_db()
        self.assertFalse(self.unverified_org.verified)

    def test_editing_locked_after_first_application(self):
        now = timezone.now()
        opp = Opportunity.objects.create(
            organizer=self.verified_org,
            category=Opportunity.Category.VOLUNTEER,
            title='Исходное название',
            duties='Исходные обязанности',
            location='НГУ',
            skills='Любые',
            capacity=3,
            workload=Decimal('2.0'),
            deadline=now + timedelta(days=2),
            starts_at=now + timedelta(days=3),
            ends_at=now + timedelta(days=3, hours=2),
            reward_types=['food'],
            reward_condition='Обед',
            status=Opportunity.Status.PUBLISHED
        )

        # Студент подаёт заявку
        Application.objects.create(
            opportunity=opp,
            student=self.student,
            comment='Хочу участвовать'
        )

        self.client.login(username='old_org@nsu.ru', password='password123')
        # Пытаемся изменить заблокированное название и увеличить места
        resp = self.client.post(f'/organizer/cards/{opp.pk}/edit/', {
            'capacity': 6,
            'title': 'Хакерское изменение названия',
            'action': 'save'
        }, follow=True)
        self.assertEqual(resp.status_code, 200)

        opp.refresh_from_db()
        # Вместимость увеличилась
        self.assertEqual(opp.capacity, 6)
        # Название НЕ изменилось!
        self.assertEqual(opp.title, 'Исходное название')
