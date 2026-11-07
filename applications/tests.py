from datetime import timedelta
from decimal import Decimal
from django.test import TestCase, Client
from django.utils import timezone
from accounts.models import User
from opportunities.models import Opportunity
from .models import Application, ApplicationEvent
from .services import (
    DuplicateApplicationError,
    NoSeatsLeftError,
    accept_application,
    apply_for_opportunity,
    cancel_application,
    complete_application,
    confirm_application,
)


class ApplicationAndF3Tests(TestCase):
    def setUp(self):
        self.client = Client()
        self.org = User.objects.create_user(
            email='org@nsu.ru',
            password='password123',
            name='Совет Студентов',
            role=User.Role.ORGANIZER,
            verified=True
        )
        self.student1 = User.objects.create_user(
            email='student1@nsu.ru',
            password='password123',
            name='Студент 1',
            role=User.Role.STUDENT
        )
        self.student2 = User.objects.create_user(
            email='student2@nsu.ru',
            password='password123',
            name='Студент 2',
            role=User.Role.STUDENT
        )
        self.student3 = User.objects.create_user(
            email='student3@nsu.ru',
            password='password123',
            name='Студент 3',
            role=User.Role.STUDENT
        )

        now = timezone.now()
        # Создаём карточку с ровно 1 свободным местом
        self.opp = Opportunity.objects.create(
            organizer=self.org,
            category=Opportunity.Category.VOLUNTEER,
            title='Тестовая роль на 1 место',
            duties='Обязанности',
            location='НГУ',
            skills='Любые',
            capacity=1,
            workload=Decimal('2.0'),
            deadline=now + timedelta(days=2),
            starts_at=now + timedelta(days=3),
            ends_at=now + timedelta(days=3, hours=2),
            reward_types=['food'],
            reward_condition='Обед',
            status=Opportunity.Status.PUBLISHED
        )

    def test_apply_and_duplicate_prevention(self):
        app = apply_for_opportunity(self.student1, self.opp, 'Хочу помочь!')
        self.assertEqual(app.status, Application.Status.PENDING)
        self.assertEqual(self.opp.occupied_seats, 0)  # PENDING не занимает место

        # Повторная подача тем же студентом
        with self.assertRaises(DuplicateApplicationError):
            apply_for_opportunity(self.student1, self.opp, 'Повторный комментарий')

    def test_accept_does_not_occupy_seat(self):
        app1 = apply_for_opportunity(self.student1, self.opp, 'Я первый')
        app2 = apply_for_opportunity(self.student2, self.opp, 'Я второй')

        # Орг принимает обоих (хотя место всего 1)
        accept_application(self.org, app1)
        accept_application(self.org, app2)

        app1.refresh_from_db()
        app2.refresh_from_db()
        self.assertEqual(app1.status, Application.Status.ACCEPTED)
        self.assertEqual(app2.status, Application.Status.ACCEPTED)
        # Место по-прежнему свободно!
        self.assertEqual(self.opp.occupied_seats, 0)
        self.assertEqual(self.opp.free_seats, 1)

    def test_confirm_occupies_seat_and_locks_last_place(self):
        app1 = apply_for_opportunity(self.student1, self.opp, 'Я первый')
        app2 = apply_for_opportunity(self.student2, self.opp, 'Я второй')

        accept_application(self.org, app1)
        accept_application(self.org, app2)

        # Студент 1 подтверждает участие первым
        confirm_application(self.student1, app1)
        app1.refresh_from_db()
        self.assertEqual(app1.status, Application.Status.CONFIRMED)
        self.assertEqual(self.opp.occupied_seats, 1)
        self.assertEqual(self.opp.free_seats, 0)

        # Студент 2 пытается подтвердить участие, когда место уже занято
        with self.assertRaises(NoSeatsLeftError):
            confirm_application(self.student2, app2)

        # Статус студента 2 остаётся ACCEPTED
        app2.refresh_from_db()
        self.assertEqual(app2.status, Application.Status.ACCEPTED)

    def test_cancel_confirmed_frees_seat_allowing_second_student(self):
        app1 = apply_for_opportunity(self.student1, self.opp, 'Я первый')
        app2 = apply_for_opportunity(self.student2, self.opp, 'Я второй')
        accept_application(self.org, app1)
        accept_application(self.org, app2)

        confirm_application(self.student1, app1)
        self.assertEqual(self.opp.free_seats, 0)

        # Студент 1 отменяет участие до начала события
        cancel_application(self.student1, app1)
        app1.refresh_from_db()
        self.assertEqual(app1.status, Application.Status.CANCELLED)
        # Место освободилось!
        self.assertEqual(self.opp.free_seats, 1)

        # Теперь студент 2 может успешно подтвердить участие!
        confirm_application(self.student2, app2)
        app2.refresh_from_db()
        self.assertEqual(app2.status, Application.Status.CONFIRMED)
        self.assertEqual(self.opp.occupied_seats, 1)

    def test_complete_requires_closed_card_and_ended_event(self):
        now = timezone.now()
        app = apply_for_opportunity(self.student1, self.opp, 'Комментарий')
        accept_application(self.org, app)
        confirm_application(self.student1, app)

        # Попытка отметить выполнение на открытом наборе и незавершённом событии
        with self.assertRaises(Exception):
            complete_application(self.org, app)

        # Закрываем набор и сдвигаем время события в прошлое
        self.opp.status = Opportunity.Status.CLOSED
        self.opp.starts_at = now - timedelta(days=2)
        self.opp.ends_at = now - timedelta(days=1)
        self.opp.save()

        app.refresh_from_db()
        complete_application(self.org, app)
        app.refresh_from_db()
        self.assertEqual(app.status, Application.Status.COMPLETED)
        # В истории есть событие
        self.assertTrue(app.events.filter(to_status=Application.Status.COMPLETED).exists())

    def test_catalog_filtering_f2(self):
        # Проверяем фильтрацию по категории, нагрузке и виду поощрения через HTTP-запросы
        resp = self.client.get('/opportunities/?category=volunteer')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Тестовая роль на 1 место')

        # Другая категория — не должна отображаться
        resp2 = self.client.get('/opportunities/?category=scientific')
        self.assertEqual(resp2.status_code, 200)
        self.assertNotContains(resp2, 'Тестовая роль на 1 место')

        # Фильтр нагрузки: наша роль 2.0 ч -> попадает в 'le2'
        resp3 = self.client.get('/opportunities/?workload=le2')
        self.assertEqual(resp3.status_code, 200)
        self.assertContains(resp3, 'Тестовая роль на 1 место')

        # Фильтр нагрузки 'gt4' -> не попадает
        resp4 = self.client.get('/opportunities/?workload=gt4')
        self.assertEqual(resp4.status_code, 200)
        self.assertNotContains(resp4, 'Тестовая роль на 1 место')

        # Фильтр поощрения: наша роль имеет 'food'
        resp5 = self.client.get('/opportunities/?reward=food')
        self.assertEqual(resp5.status_code, 200)
        self.assertContains(resp5, 'Тестовая роль на 1 место')

        # Невалидный enum категории -> 400 Bad Request по ТЗ
        resp_bad = self.client.get('/opportunities/?category=invalid_cat')
        self.assertEqual(resp_bad.status_code, 400)
