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


def run():
    now = timezone.now()
    print(f'Текущее время в системе: {now}')

    # Обновляем дедлайны старых активных карточек, чтобы они не истекли
    for opp in Opportunity.objects.filter(status=Opportunity.Status.PUBLISHED):
        if opp.deadline and opp.deadline < now:
            opp.deadline = now + timedelta(days=5, hours=4)
            opp.starts_at = now + timedelta(days=6, hours=10)
            opp.ends_at = now + timedelta(days=6, hours=14)
            opp.save(update_fields=['deadline', 'starts_at', 'ends_at'])
            print(f'Обновлены даты для карточки: {opp.title}')

    # Создаём новых верифицированных организаторов НГУ
    orgs_data = [
        ('career@nsu.ru', 'Центр развития карьеры НГУ'),
        ('fen_bio@nsu.ru', 'Кафедра молекулярной биологии ФЕН НГУ'),
        ('eco_club@nsu.ru', 'Экоклуб НГУ «Green NSU»'),
        ('sport_nsu@nsu.ru', 'Спортивный клуб НГУ'),
        ('library@nsu.ru', 'Научная библиотека НГУ'),
        ('media_nsu@nsu.ru', 'Студенческий медиацентр NSU LIFE'),
        ('inp_phys@nsu.ru', 'Институт ядерной физики СО РАН / ФФ НГУ'),
    ]

    org_objs = {}
    for email, name in orgs_data:
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'name': name,
                'role': User.Role.ORGANIZER,
                'verified': True,
                'verified_at': now - timedelta(days=30),
            }
        )
        if created:
            user.set_password('dvizh2026')
            user.save()
            print(f'Создан организатор: {name} ({email})')
        org_objs[email] = user

    # Существующие организаторы
    events_org = User.objects.filter(email='events@nsu.ru').first()
    fit_org = User.objects.filter(email='fit_lab@nsu.ru').first()
    inter_org = User.objects.filter(email='inter_dept@nsu.ru').first()

    # Студенты для заполнения мест
    student_ivan = User.objects.filter(email='ivan.ivanov@nsu.ru').first()
    student_anna = User.objects.filter(email='anna.smirnova@nsu.ru').first()
    student_dmitry = User.objects.filter(email='dmitry.popov@nsu.ru').first()
    student_elena = User.objects.filter(email='elena.kuznetsova@nsu.ru').first()

    new_events = [
        # --- НАУЧНЫЕ ПРОЕКТЫ ---
        {
            'organizer': org_objs['fen_bio@nsu.ru'],
            'category': Opportunity.Category.SCIENTIFIC,
            'title': 'Биоинформатический анализ мутаций устойчивости штаммов бактерий',
            'duties': 'Первичная обработка NGS-прочтений (FastQC, Trimmomatic), картирование геномов на референс (BWA), поиск однонуклеотидных полиморфизмов (SNP) и оформление отчёта для лаборатории.',
            'location': 'Лабораторный корпус НГУ, ауд. 412 (Лаборатория биоинформатики)',
            'workload': Decimal('25.0'),
            'capacity': 2,
            'skills': 'Базовый Linux (Bash), понимание основ генетики, опыт в Python или R приветствуется.',
            'deadline': now + timedelta(days=6, hours=18),
            'starts_at': now + timedelta(days=8, hours=10),
            'ends_at': now + timedelta(days=35, hours=18),
            'reward_types': [Opportunity.RewardType.MONEY, Opportunity.RewardType.EXPERIENCE],
            'reward_condition': 'Вознаграждение 20 000 руб. по договору ГПХ и соавторство в научной публикации Scopus.',
        },
        {
            'organizer': fit_org or org_objs['media_nsu@nsu.ru'],
            'category': Opportunity.Category.SCIENTIFIC,
            'title': 'Разработка 3D-модели нового кампуса НГУ в Unreal Engine 5',
            'duties': 'Создание low-poly и high-poly ассетов корпусов нового кампуса, настройка материалов Nanite и освещения Lumen, интеграция интерактивной навигации для виртуального гида НГУ.',
            'location': 'Новый корпус НГУ, Центр виртуальной реальности, ауд. 2311',
            'workload': Decimal('40.0'),
            'capacity': 3,
            'skills': 'Blender или 3ds Max, основы Unreal Engine 5, понимание PBR-текстурирования.',
            'deadline': now + timedelta(days=7, hours=20),
            'starts_at': now + timedelta(days=9, hours=14),
            'ends_at': now + timedelta(days=45, hours=19),
            'reward_types': [Opportunity.RewardType.MONEY, Opportunity.RewardType.EXPERIENCE, Opportunity.RewardType.MERCH],
            'reward_condition': 'Оплата 30 000 руб. по договору ГПХ по факту приёмки сцены + брендированный худи разработчика лаборатории.',
        },
        {
            'organizer': org_objs['inp_phys@nsu.ru'],
            'category': Opportunity.Category.SCIENTIFIC,
            'title': 'Моделирование треков элементарных частиц для детектора КМД-3',
            'duties': 'Работа с пакетом Geant4, моделирование отклика калориметра детектора КМД-3 на электрон-позитронном коллайдере ВЭПП-2000, сравнение модельных данных с экспериментальными.',
            'location': 'ИЯФ СО РАН им. Будкера, корпус ВЭПП-2000',
            'workload': Decimal('16.0'),
            'capacity': 2,
            'skills': 'C++ или Python, основы теории вероятностей и ядерной физики.',
            'deadline': now + timedelta(days=8, hours=12),
            'starts_at': now + timedelta(days=10, hours=11),
            'ends_at': now + timedelta(days=30, hours=17),
            'reward_types': [Opportunity.RewardType.EXPERIENCE, Opportunity.RewardType.TICKET],
            'reward_condition': 'Включение в научную группу коллайдера, персональный пропуск в ИЯФ и оплата поездки на всероссийскую конференцию.',
        },
        {
            'organizer': inter_org or events_org,
            'category': Opportunity.Category.SCIENTIFIC,
            'title': 'Разметка синтаксического корпуса параллельных русско-китайских текстов',
            'duties': 'Проверка автоматического выравнивания предложений в корпусе общественно-политических текстов, аннотация терминов и составление глоссария редких идиом.',
            'location': 'Главный корпус НГУ, кафедра востоковедения, ауд. 215',
            'workload': Decimal('8.0'),
            'capacity': 4,
            'skills': 'Китайский язык (HSK 4+), внимательность к деталям, грамотный русский язык.',
            'deadline': now + timedelta(days=5, hours=22),
            'starts_at': now + timedelta(days=7, hours=14),
            'ends_at': now + timedelta(days=14, hours=18),
            'reward_types': [Opportunity.RewardType.EXPERIENCE, Opportunity.RewardType.FOOD],
            'reward_condition': 'Зачёт производственной/языковой практики, сертификат кафедры востоковедения и кофе-брейки на сменах.',
        },

        # --- ВОЛОНТЁРСКИЕ РОЛИ ---
        {
            'organizer': org_objs['eco_club@nsu.ru'],
            'category': Opportunity.Category.VOLUNTEER,
            'title': 'Координатор раздельного сбора отходов на Экофестивале НГУ',
            'duties': 'Инструктаж участников по сортировке вторсырья (пластик, макулатура, батарейки, крышечки), приём и взвешивание фракций, выдача эко-призов.',
            'location': 'Внутренний двор Нового корпуса НГУ',
            'workload': Decimal('3.0'),
            'capacity': 6,
            'skills': 'Опыт не требуется. Интерес к экологическому образу жизни.',
            'deadline': now + timedelta(days=4, hours=15),
            'starts_at': now + timedelta(days=5, hours=12),
            'ends_at': now + timedelta(days=5, hours=15),
            'reward_types': [Opportunity.RewardType.MERCH, Opportunity.RewardType.FOOD],
            'reward_condition': 'Хлопковый эко-шоппер с символикой Green NSU, термокружка и вегетарианский горячий ланч.',
        },
        {
            'organizer': events_org,
            'category': Opportunity.Category.VOLUNTEER,
            'title': 'Волонтёр-секретарь секции на конференции МНСК-2026',
            'duties': 'Встреча докладчиков и членов жюри в аудитории, запуск презентаций на проекторе, хронометраж докладов (регламент 10 мин) и передача микрофона в зал.',
            'location': 'Новый корпус НГУ, блок 3, поточная аудитория 3107',
            'workload': Decimal('4.0'),
            'capacity': 8,
            'skills': 'Опыт не требуется. Вежливость, пунктуальность и базовое умение работать с PowerPoint/PDF.',
            'deadline': now + timedelta(days=5, hours=19),
            'starts_at': now + timedelta(days=6, hours=9),
            'ends_at': now + timedelta(days=6, hours=13),
            'reward_types': [Opportunity.RewardType.EXPERIENCE, Opportunity.RewardType.MERCH, Opportunity.RewardType.FOOD],
            'reward_condition': 'Благодарственное письмо ректора НГУ, брендированный блокнот и ручка МНСК, талон на обед в столовой.',
        },
        {
            'organizer': org_objs['sport_nsu@nsu.ru'],
            'category': Opportunity.Category.VOLUNTEER,
            'title': 'Судья-хронометрист и навигатор на Кубке ректора по мини-футболу',
            'duties': 'Ведение электронного табло времени матчей, фиксация забитых мячей и нарушений в судейском протоколе, навигация команд по раздевалкам.',
            'location': 'Спортивный комплекс НГУ, игровой зал №1',
            'workload': Decimal('2.0'),
            'capacity': 4,
            'skills': 'Базовое знание правил мини-футбола, внимательность.',
            'deadline': now + timedelta(days=3, hours=18),
            'starts_at': now + timedelta(days=4, hours=16),
            'ends_at': now + timedelta(days=4, hours=18),
            'reward_types': [Opportunity.RewardType.MERCH, Opportunity.RewardType.TICKET],
            'reward_condition': 'Спортивная футболка сборной НГУ и бесплатный абонемент в тренажёрный зал Спорткомплекса на 1 месяц.',
        },
        {
            'organizer': events_org,
            'category': Opportunity.Category.VOLUNTEER,
            'title': 'Помощник координатора на сибирском турнире «Что? Где? Когда?»',
            'duties': 'Сбор карточек с ответами от команд знатоков («ласточка»), подсчёт баллов в турнирной таблице, раздача бланков апелляций.',
            'location': 'Новый корпус НГУ, студенческая столовая, 2 этаж',
            'workload': Decimal('2.5'),
            'capacity': 3,
            'skills': 'Быстрота реакции, аккуратный почерк, внимательность.',
            'deadline': now + timedelta(days=4, hours=14),
            'starts_at': now + timedelta(days=5, hours=17),
            'ends_at': now + timedelta(days=5, hours=19, minutes=30),
            'reward_types': [Opportunity.RewardType.FOOD, Opportunity.RewardType.MERCH],
            'reward_condition': 'Пицца для волонтёров после турнира, фирменный значок и блокнот клуба интеллектуальных игр.',
            'fill_full': True,  # Сделаем все места занятыми для демонстрации бейджа "Мест нет"
        },

        # --- РАЗОВЫЕ ЗАДАЧИ ---
        {
            'organizer': org_objs['career@nsu.ru'],
            'category': Opportunity.Category.ONE_OFF,
            'title': 'Ассистент координатора на Ярмарке IT-карьеры Академгородка',
            'duties': 'Помощь компаниям-экспонентам (Яндекс, 2ГИС, ЦФТ, Сбер) в сборке стендов, регистрация студентов-соискателей, раздача навигационных карт ярмарки.',
            'location': 'Холл 2 этажа Нового корпуса НГУ',
            'workload': Decimal('3.5'),
            'capacity': 6,
            'skills': 'Опыт не требуется. Коммуникабельность и опрятный внешний вид.',
            'deadline': now + timedelta(days=4, hours=20),
            'starts_at': now + timedelta(days=5, hours=11),
            'ends_at': now + timedelta(days=5, hours=14, minutes=30),
            'reward_types': [Opportunity.RewardType.FOOD, Opportunity.RewardType.MERCH, Opportunity.RewardType.EXPERIENCE],
            'reward_condition': 'Эксклюзивный мерч компаний-партнёров, горячий обед и закрытый нетворкинг с HR-директорами после мероприятия.',
        },
        {
            'organizer': org_objs['library@nsu.ru'],
            'category': Opportunity.Category.ONE_OFF,
            'title': 'Оцифровка редких рукописей и чертежей основателей Академгородка',
            'duties': 'Бережная укладка архивных материалов на планетарный сканер Элар, контроль качества оптического распознавания (OCR) и каталогизация PDF-файлов.',
            'location': 'Научная библиотека НГУ, зал редких фондов (к. 114)',
            'workload': Decimal('4.0'),
            'capacity': 3,
            'skills': 'Аккуратность, бережное обращение со старыми документами.',
            'deadline': now + timedelta(days=5, hours=12),
            'starts_at': now + timedelta(days=6, hours=13),
            'ends_at': now + timedelta(days=6, hours=17),
            'reward_types': [Opportunity.RewardType.EXPERIENCE],
            'reward_condition': 'Опыт работы с музейным архивным оборудованием, именная благодарность от Научной библиотеки НГУ.',
        },
        {
            'organizer': org_objs['media_nsu@nsu.ru'],
            'category': Opportunity.Category.ONE_OFF,
            'title': 'Оператор и монтажёр серии VK Клипов о жизни в общежитиях НГУ',
            'duties': 'Съёмка 4 коротких вертикальных динамичных роликов (до 60 сек) по согласованному сценарию: быт студентов, боталки, спортплощадки, кухня.',
            'location': 'Кампус НГУ, студгородок на ул. Пирогова (общежития №6, 7, 8)',
            'workload': Decimal('5.0'),
            'capacity': 2,
            'skills': 'Смартфон с хорошей камерой или зеркалка, навыки монтажа в CapCut/Premiere.',
            'deadline': now + timedelta(days=6, hours=23),
            'starts_at': now + timedelta(days=7, hours=15),
            'ends_at': now + timedelta(days=12, hours=20),
            'reward_types': [Opportunity.RewardType.MONEY, Opportunity.RewardType.MERCH],
            'reward_condition': 'Оплата 6 000 руб. за 4 принятых клипа + мерч медиацентра NSU LIFE.',
        },
        {
            'organizer': events_org,
            'category': Opportunity.Category.ONE_OFF,
            'title': 'Дежурный координатор на Всесибирской открытой олимпиаде школьников',
            'duties': 'Встреча участников у турникетов СУНЦ НГУ, распределение по аудиториям тестирования, раздача черновиков и дежурство в коридоре этажа.',
            'location': 'Учебный корпус СУНЦ НГУ (ФМШ), ул. Ляпунова 3',
            'workload': Decimal('3.0'),
            'capacity': 10,
            'skills': 'Опыт не требуется. Знание корпуса ФМШ приветствуется.',
            'deadline': now + timedelta(days=2, hours=22),
            'starts_at': now + timedelta(days=3, hours=9),
            'ends_at': now + timedelta(days=3, hours=12),
            'reward_types': [Opportunity.RewardType.FOOD, Opportunity.RewardType.MERCH],
            'reward_condition': 'Брендированный значок и футболка СУНЦ НГУ, сытный комплексный обед в легендарной столовой ФМШ.',
        },
        {
            'organizer': inter_org or events_org,
            'category': Opportunity.Category.ONE_OFF,
            'title': 'Помощь в настройке звука и света на акустическом квартирнике в НГУ',
            'duties': 'Расстановка микрофонных стоек, подключение гитарных комбиков и DI-боксов, проверка звука (soundcheck) и управление диммером тёплого сценического света.',
            'location': 'Арт-клуб НГУ, цокольный этаж общежития №10',
            'workload': Decimal('1.5'),
            'capacity': 2,
            'skills': 'Базовое понимание аудиокоммутации (XLR, Jack 6.3), любовь к живой музыке.',
            'deadline': now + timedelta(days=3, hours=16),
            'starts_at': now + timedelta(days=3, hours=18),
            'ends_at': now + timedelta(days=3, hours=19, minutes=30),
            'reward_types': [Opportunity.RewardType.TICKET, Opportunity.RewardType.FOOD],
            'reward_condition': 'VIP-проходка на весь концерт для себя и друга + чай с выпечкой в гримёрке артистов.',
        },
        {
            'organizer': inter_org or events_org,
            'category': Opportunity.Category.ONE_OFF,
            'title': 'Сортировка коллекции образцов минералов Сибири и Дальнего Востока',
            'duties': 'Распаковка полевых сборов геологов, сверка полевых номеров с полевыми дневниками, наклейка этикеток и размещение в витринах музея.',
            'location': 'Главный корпус НГУ, Геологический музей, ауд. 104',
            'workload': Decimal('2.0'),
            'capacity': 3,
            'skills': 'Аккуратность, интерес к геологии и минералам.',
            'deadline': now + timedelta(days=4, hours=17),
            'starts_at': now + timedelta(days=5, hours=14),
            'ends_at': now + timedelta(days=5, hours=16),
            'reward_types': [Opportunity.RewardType.MERCH, Opportunity.RewardType.EXPERIENCE],
            'reward_condition': 'Сувенирный образец сибирского чароита в личную коллекцию и закрытая экскурсия от профессора ГГФ.',
        },
    ]

    count_created = 0
    for data in new_events:
        fill_full = data.pop('fill_full', False)
        title = data['title']

        # Если уже существует, пропускаем или обновляем
        opp, created = Opportunity.objects.get_or_create(
            title=title,
            defaults={
                **data,
                'status': Opportunity.Status.PUBLISHED,
                'published_at': now - timedelta(hours=2),
            }
        )
        if created:
            count_created += 1
            print(f'Создана новая роль: «{title}» ({opp.get_category_display()}, {opp.workload} ч.)')

            if fill_full:
                # Заполняем места (например, для ЧГК)
                students = [student_ivan, student_anna, student_dmitry]
                for st in students[:opp.capacity]:
                    if st:
                        app = Application.objects.create(
                            opportunity=opp,
                            student=st,
                            comment='С удовольствием помогу на турнире ЧГК!',
                            status=Application.Status.CONFIRMED,
                            decided_at=now - timedelta(hours=1),
                            confirmed_at=now - timedelta(minutes=30)
                        )
                        ApplicationEvent.objects.create(application=app, actor=st, from_status=None, to_status=Application.Status.PENDING)
                        ApplicationEvent.objects.create(application=app, actor=opp.organizer, from_status=Application.Status.PENDING, to_status=Application.Status.ACCEPTED)
                        ApplicationEvent.objects.create(application=app, actor=st, from_status=Application.Status.ACCEPTED, to_status=Application.Status.CONFIRMED)
                print(f' -> Роль «{title}» полностью заполнена (статус: «Мест нет»).')

    print(f'\nГотово! Добавлено {count_created} новых колоритных ролей НГУ.')
    print(f'Всего актуальных возможностей в каталоге: {Opportunity.objects.filter(status=Opportunity.Status.PUBLISHED).count()}')


if __name__ == '__main__':
    run()
