import os
import django
from datetime import timedelta
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.utils import timezone
from accounts.models import User
from opportunities.models import Opportunity
from applications.models import Application, ApplicationEvent


def seed():
    print('Очистка предыдущих тестовых данных...')
    ApplicationEvent.objects.all().delete()
    Application.objects.all().delete()
    Opportunity.objects.all().delete()
    User.objects.all().delete()

    print('Создание пользователей...')
    # 1. Модератор
    moderator = User.objects.create_superuser(
        email='moderator@nsu.ru',
        password='dvizh2026',
        name='Модератор платформы НГУ',
    )
    print(f'Создан модератор: {moderator.email}')

    # 2. Подтверждённые организаторы
    org_studsovet = User.objects.create_user(
        email='events@nsu.ru',
        password='dvizh2026',
        name='Совет Студентов НГУ',
        role=User.Role.ORGANIZER,
        verified=True,
        verified_at=timezone.now()
    )

    org_fit = User.objects.create_user(
        email='fit_lab@nsu.ru',
        password='dvizh2026',
        name='Лаборатория ИИ ФИТ НГУ',
        role=User.Role.ORGANIZER,
        verified=True,
        verified_at=timezone.now()
    )

    org_youth = User.objects.create_user(
        email='inter_dept@nsu.ru',
        password='dvizh2026',
        name='Управление молодёжной политики НГУ',
        role=User.Role.ORGANIZER,
        verified=True,
        verified_at=timezone.now()
    )

    # 3. Неподтверждённый организатор (для демонстрации модерации)
    org_robotics = User.objects.create_user(
        email='robotics@nsu.ru',
        password='dvizh2026',
        name='Клуб Робототехники НГУ',
        role=User.Role.ORGANIZER,
        verified=False
    )

    # 4. Студенты
    student_ivan = User.objects.create_user(
        email='ivan.ivanov@nsu.ru',
        password='dvizh2026',
        name='Иван Иванов',
        role=User.Role.STUDENT
    )
    student_anna = User.objects.create_user(
        email='anna.smirnova@nsu.ru',
        password='dvizh2026',
        name='Анна Смирнова',
        role=User.Role.STUDENT
    )
    student_dmitry = User.objects.create_user(
        email='dmitry.popov@nsu.ru',
        password='dvizh2026',
        name='Дмитрий Попов',
        role=User.Role.STUDENT
    )
    student_elena = User.objects.create_user(
        email='elena.kuznetsova@nsu.ru',
        password='dvizh2026',
        name='Елена Кузнецова',
        role=User.Role.STUDENT
    )
    print('Пользователи успешно созданы.')

    now = timezone.now()

    # --- Карточка 1: Хакатон (Совет Студентов) ---
    opp1 = Opportunity.objects.create(
        organizer=org_studsovet,
        category=Opportunity.Category.ONE_OFF,
        title='Помощь на регистрации участников Инженерного хакатона НГУ',
        duties='Встреча участников у стойки регистрации в Новом корпусе НГУ, сверка паспортов со списком зарегистрированных команд, выдача приветственных бейджей и пакетов участников.',
        starts_at=now + timedelta(days=5, hours=10),
        ends_at=now + timedelta(days=5, hours=14),
        deadline=now + timedelta(days=4, hours=18),
        location='Новый корпус НГУ, ул. Пирогова 1, холл 1 этажа',
        workload=Decimal('4.0'),
        skills='Опыт не требуется. Доброжелательность, пунктуальность и внимательность.',
        capacity=5,
        reward_types=[Opportunity.RewardType.FOOD, Opportunity.RewardType.MERCH],
        reward_condition='Горячий комплексный обед и фирменная толстовка организатора хакатона после смены.',
        status=Opportunity.Status.PUBLISHED,
        published_at=now - timedelta(days=1)
    )

    # Заявки на карточку 1:
    # Иван — подтверждён (занимает место)
    app1_ivan = Application.objects.create(
        opportunity=opp1,
        student=student_ivan,
        comment='Участвовал волонтёром в прошлом семестре на Хакатоне НГУ, готов помочь на регистрации!',
        status=Application.Status.CONFIRMED,
        decided_at=now - timedelta(hours=8),
        confirmed_at=now - timedelta(hours=6)
    )
    ApplicationEvent.objects.create(application=app1_ivan, actor=student_ivan, from_status=None, to_status=Application.Status.PENDING)
    ApplicationEvent.objects.create(application=app1_ivan, actor=org_studsovet, from_status=Application.Status.PENDING, to_status=Application.Status.ACCEPTED)
    ApplicationEvent.objects.create(application=app1_ivan, actor=student_ivan, from_status=Application.Status.ACCEPTED, to_status=Application.Status.CONFIRMED)

    # Анна — подтверждена (занимает место)
    app1_anna = Application.objects.create(
        opportunity=opp1,
        student=student_anna,
        comment='Студентка 2 курса ГИ, свободна в субботу с 9:30, люблю общаться с людьми.',
        status=Application.Status.CONFIRMED,
        decided_at=now - timedelta(hours=5),
        confirmed_at=now - timedelta(hours=3)
    )
    ApplicationEvent.objects.create(application=app1_anna, actor=student_anna, from_status=None, to_status=Application.Status.PENDING)
    ApplicationEvent.objects.create(application=app1_anna, actor=org_studsovet, from_status=Application.Status.PENDING, to_status=Application.Status.ACCEPTED)
    ApplicationEvent.objects.create(application=app1_anna, actor=student_anna, from_status=Application.Status.ACCEPTED, to_status=Application.Status.CONFIRMED)

    # Дмитрий — принят организатором (ждёт подтверждения студентом, место НЕ занимает)
    app1_dmitry = Application.objects.create(
        opportunity=opp1,
        student=student_dmitry,
        comment='Хочу получить опыт координации мероприятий в НГУ.',
        status=Application.Status.ACCEPTED,
        decided_at=now - timedelta(hours=2)
    )
    ApplicationEvent.objects.create(application=app1_dmitry, actor=student_dmitry, from_status=None, to_status=Application.Status.PENDING)
    ApplicationEvent.objects.create(application=app1_dmitry, actor=org_studsovet, from_status=Application.Status.PENDING, to_status=Application.Status.ACCEPTED)

    # Елена — отправлена (ждёт рассмотрения организатором)
    app1_elena = Application.objects.create(
        opportunity=opp1,
        student=student_elena,
        comment='Есть опыт работы волонтёром на конференциях.',
        status=Application.Status.PENDING
    )
    ApplicationEvent.objects.create(application=app1_elena, actor=student_elena, from_status=None, to_status=Application.Status.PENDING)

    # --- Карточка 2: Интернеделя (ПОЛНОСТЬЮ ЗАПОЛНЕНА — "Мест нет") ---
    opp2 = Opportunity.objects.create(
        organizer=org_youth,
        category=Opportunity.Category.VOLUNTEER,
        title='Волонтёр секции Интернедели НГУ — координация делегаций',
        duties='Сопровождение участников фестиваля, помощь на информационных стойках, навигация по кампусу Академгородка.',
        starts_at=now + timedelta(days=7, hours=12),
        ends_at=now + timedelta(days=7, hours=15, minutes=30),
        deadline=now + timedelta(days=6, hours=12),
        location='Главный корпус НГУ, ул. Пирогова 2',
        workload=Decimal('3.5'),
        skills='Английский язык на разговорном уровне (B1+), знание кампуса НГУ.',
        capacity=3,
        reward_types=[Opportunity.RewardType.EXPERIENCE, Opportunity.RewardType.MERCH],
        reward_condition='Официальная верификация волонтёрских часов на Добро.рф, комплект мерча Интернедели.',
        status=Opportunity.Status.PUBLISHED,
        published_at=now - timedelta(days=2)
    )
    # Заполняем все 3 места (Иван, Анна, Дмитрий подтверждены)
    for st, comm in [
        (student_ivan, 'Свободно говорю на английском, готов сопровождать группу.'),
        (student_anna, 'Изучаю лингвистику, была волонтёром Интернедели в прошлом году.'),
        (student_dmitry, 'Живу в общежитии рядом с Главным корпусом, всё знаю.')
    ]:
        a = Application.objects.create(
            opportunity=opp2,
            student=st,
            comment=comm,
            status=Application.Status.CONFIRMED,
            decided_at=now - timedelta(days=1),
            confirmed_at=now - timedelta(hours=12)
        )
        ApplicationEvent.objects.create(application=a, actor=st, from_status=None, to_status=Application.Status.PENDING)
        ApplicationEvent.objects.create(application=a, actor=org_youth, from_status=Application.Status.PENDING, to_status=Application.Status.ACCEPTED)
        ApplicationEvent.objects.create(application=a, actor=st, from_status=Application.Status.ACCEPTED, to_status=Application.Status.CONFIRMED)

    # --- Карточка 3: Научный проект ИИ (ФИТ НГУ) ---
    opp3 = Opportunity.objects.create(
        organizer=org_fit,
        category=Opportunity.Category.SCIENTIFIC,
        title='Разработка модуля анализа студенческих отзывов на базе LLM',
        duties='Предобработка русскоязычного датасета отзывов студентов НГУ, тонкая настройка открытой языковой модели (fine-tuning LoRA), интеграция инференса через FastAPI.',
        starts_at=now + timedelta(days=10, hours=14),
        ends_at=now + timedelta(days=30, hours=18),
        deadline=now + timedelta(days=8, hours=23),
        location='Лаборатория ИИ ФИТ НГУ, ауд. 4212',
        workload=Decimal('30.0'),
        skills='Python, PyTorch / Transformers, базовое понимание NLP и REST API.',
        capacity=2,
        reward_types=[Opportunity.RewardType.MONEY, Opportunity.RewardType.EXPERIENCE],
        reward_condition='Вознаграждение 25 000 руб. по договору ГПХ после успешной приёмки кода и отчёта.',
        status=Opportunity.Status.PUBLISHED,
        published_at=now - timedelta(days=1)
    )
    app3 = Application.objects.create(
        opportunity=opp3,
        student=student_elena,
        comment='Студентка 3 курса ФИТ, писала курсовую по трансформерам и LoRA. Ссылка на GitHub в резюме.',
        status=Application.Status.CONFIRMED,
        decided_at=now - timedelta(hours=4),
        confirmed_at=now - timedelta(hours=2)
    )
    ApplicationEvent.objects.create(application=app3, actor=student_elena, from_status=None, to_status=Application.Status.PENDING)
    ApplicationEvent.objects.create(application=app3, actor=org_fit, from_status=Application.Status.PENDING, to_status=Application.Status.ACCEPTED)
    ApplicationEvent.objects.create(application=app3, actor=student_elena, from_status=Application.Status.ACCEPTED, to_status=Application.Status.CONFIRMED)

    # --- Карточка 4: День открытых дверей (короткая задача <= 2 ч) ---
    Opportunity.objects.create(
        organizer=org_studsovet,
        category=Opportunity.Category.VOLUNTEER,
        title='Навигация абитуриентов на Дне открытых дверей НГУ',
        duties='Координация потока школьников и родителей на переходе между Главным и Новым корпусами, раздача буклетов факультетов.',
        starts_at=now + timedelta(days=3, hours=11),
        ends_at=now + timedelta(days=3, hours=13),
        deadline=now + timedelta(days=2, hours=20),
        location='Переход между корпусами НГУ',
        workload=Decimal('2.0'),  # Тестирует фильтр <= 2 ч!
        skills='Опыт не требуется. Знание расположения аудиторий НГУ.',
        capacity=8,
        reward_types=[Opportunity.RewardType.MERCH, Opportunity.RewardType.FOOD],
        reward_condition='Брендированная футболка НГУ и ланч-бокс в столовой.',
        status=Opportunity.Status.PUBLISHED,
        published_at=now
    )

    # --- Карточка 5: Клуб робототехники (НА ПРОВЕРКЕ У МОДЕРАТОРА) ---
    Opportunity.objects.create(
        organizer=org_robotics,
        category=Opportunity.Category.ONE_OFF,
        title='Сборка полигонов для студенческого турнира роботов',
        duties='Монтаж деревянных и пластиковых элементов трека соревнований, установка датчиков линии и освещения.',
        starts_at=now + timedelta(days=9, hours=10),
        ends_at=now + timedelta(days=9, hours=15),
        deadline=now + timedelta(days=7, hours=22),
        location='Мастерская Клуба робототехники, цокольный этаж общежития 1б',
        workload=Decimal('5.0'),
        skills='Умение работать с базовым ручным инструментом (отвёртка, шуруповёрт).',
        capacity=4,
        reward_types=[Opportunity.RewardType.FOOD, Opportunity.RewardType.EXPERIENCE],
        reward_condition='Большая пицца на команду и бесплатный доступ к 3D-принтерам мастерской.',
        status=Opportunity.Status.PENDING_REVIEW  # Ожидает в очереди модерации!
    )

    # --- Карточка 6: Завершённое мероприятие с отметкой COMPLETED ---
    opp6 = Opportunity.objects.create(
        organizer=org_fit,
        category=Opportunity.Category.ONE_OFF,
        title='Проведение мастер-класса по Git и GitHub для первокурсников',
        duties='Провести практическое занятие в компьютерном классе для групп 1 курса.',
        starts_at=now - timedelta(days=5, hours=16),
        ends_at=now - timedelta(days=5, hours=18),
        deadline=now - timedelta(days=7, hours=12),
        location='Новый корпус НГУ, ауд. 2215',
        workload=Decimal('2.0'),
        skills='Уверенное владение Git (commit, branch, merge, pull request).',
        capacity=1,
        reward_types=[Opportunity.RewardType.EXPERIENCE, Opportunity.RewardType.MERCH],
        reward_condition='Брендированный свитшот ФИТ НГУ и сертификат спикера.',
        status=Opportunity.Status.CLOSED,
        published_at=now - timedelta(days=8),
        closed_at=now - timedelta(days=4)
    )
    app6 = Application.objects.create(
        opportunity=opp6,
        student=student_ivan,
        comment='Преподавал основы программирования в физмат-школе, с радостью проведу!',
        status=Application.Status.COMPLETED,
        decided_at=now - timedelta(days=6),
        confirmed_at=now - timedelta(days=6, hours=2)
    )
    ApplicationEvent.objects.create(application=app6, actor=student_ivan, from_status=None, to_status=Application.Status.PENDING)
    ApplicationEvent.objects.create(application=app6, actor=org_fit, from_status=Application.Status.PENDING, to_status=Application.Status.ACCEPTED)
    ApplicationEvent.objects.create(application=app6, actor=student_ivan, from_status=Application.Status.ACCEPTED, to_status=Application.Status.CONFIRMED)
    ApplicationEvent.objects.create(application=app6, actor=org_fit, from_status=Application.Status.CONFIRMED, to_status=Application.Status.COMPLETED)

    print('=' * 60)
    print('База данных успешно наполнена тестовыми данными «Движ НГУ»!')
    print('Тестовые аккаунты (пароль у всех: dvizh2026):')
    print('  - Модератор:       moderator@nsu.ru')
    print('  - Орг. (Совет):    events@nsu.ru')
    print('  - Орг. (ФИТ):      fit_lab@nsu.ru')
    print('  - Орг. (Новый):    robotics@nsu.ru (в очереди модерации)')
    print('  - Студент (Иван):  ivan.ivanov@nsu.ru')
    print('  - Студентка (Анна): anna.smirnova@nsu.ru')
    print('=' * 60)


if __name__ == '__main__':
    seed()
