from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Opportunity(models.Model):
    class Category(models.TextChoices):
        SCIENTIFIC = 'scientific', 'Научный проект'
        VOLUNTEER = 'volunteer', 'Волонтёрская роль'
        ONE_OFF = 'one_off', 'Разовая задача'

    class RewardType(models.TextChoices):
        EXPERIENCE = 'experience', 'Опыт'
        MERCH = 'merch', 'Мерч'
        FOOD = 'food', 'Питание'
        TICKET = 'ticket', 'Билет'
        MONEY = 'money', 'Денежное вознаграждение'
        NONE = 'none', 'Без вознаграждения'

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Черновик'
        PENDING_REVIEW = 'PENDING_REVIEW', 'На проверке'
        PUBLISHED = 'PUBLISHED', 'Опубликовано'
        CLOSED = 'CLOSED', 'Набор закрыт'

    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='opportunities',
        verbose_name='Организатор'
    )
    category = models.CharField(
        'Категория',
        max_length=30,
        choices=Category.choices,
        default=Category.VOLUNTEER
    )
    title = models.CharField('Название роли', max_length=120)
    duties = models.TextField('Обязанности', max_length=2000)
    starts_at = models.DateTimeField('Дата и время начала', null=True, blank=True)
    ends_at = models.DateTimeField('Дата и время окончания', null=True, blank=True)
    deadline = models.DateTimeField('Срок отклика (дедлайн)', null=True, blank=True)
    location = models.CharField('Место проведения', max_length=200)
    workload = models.DecimalField(
        'Суммарная нагрузка (в часах)',
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True
    )
    skills = models.TextField('Требуемые навыки', max_length=500)
    capacity = models.PositiveIntegerField('Число мест', default=1)
    reward_types = models.JSONField(
        'Виды поощрения',
        default=list,
        help_text='Список выбранных кодов поощрения'
    )
    reward_condition = models.TextField(
        'Условие получения поощрения',
        max_length=500,
        blank=True,
        default=''
    )

    status = models.CharField(
        'Статус',
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True
    )
    moderation_note = models.TextField('Причина возврата / заметка модератора', max_length=500, blank=True, default='')
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_opportunities',
        verbose_name='Проверил модератор'
    )

    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)
    published_at = models.DateTimeField('Опубликовано', null=True, blank=True)
    closed_at = models.DateTimeField('Закрыто', null=True, blank=True)

    class Meta:
        verbose_name = 'Возможность'
        verbose_name_plural = 'Возможности'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} ({self.get_status_display()})'

    @property
    def occupied_seats(self):
        # Место занимают подтверждённые и выполненные заявки
        return self.applications.filter(status__in=['CONFIRMED', 'COMPLETED']).count()

    @property
    def free_seats(self):
        return max(0, self.capacity - self.occupied_seats)

    @property
    def is_full(self):
        return self.occupied_seats >= self.capacity

    @property
    def is_active_for_catalog(self):
        if self.status != self.Status.PUBLISHED:
            return False
        if not self.deadline:
            return False
        return self.deadline > timezone.now()

    @property
    def has_applications(self):
        return self.applications.exists()

    @property
    def reward_type_labels(self):
        labels_map = dict(self.RewardType.choices)
        return [labels_map.get(t, t) for t in self.reward_types]

    def validate_for_publication(self):
        """Полная валидация обязательных полей для отправки на проверку или публикации."""
        errors = {}
        if not self.title or not self.title.strip():
            errors['title'] = 'Название роли обязательно.'
        if not self.duties or not self.duties.strip():
            errors['duties'] = 'Обязанности обязательны.'
        if not self.location or not self.location.strip():
            errors['location'] = 'Место проведения обязательно.'
        if not self.skills or not self.skills.strip():
            errors['skills'] = 'Укажите требуемые навыки (например, "Опыт не требуется").'

        now = timezone.now()
        if not self.deadline:
            errors['deadline'] = 'Укажите срок отклика (дедлайн).'
        elif self.deadline <= now:
            errors['deadline'] = 'Срок отклика должен быть позже текущего времени.'

        if not self.starts_at:
            errors['starts_at'] = 'Укажите дату и время начала.'
        elif self.deadline and self.starts_at < self.deadline:
            errors['starts_at'] = 'Дата начала не может быть раньше срока отклика.'

        if not self.ends_at:
            errors['ends_at'] = 'Укажите дату и время окончания.'
        elif self.starts_at and self.ends_at <= self.starts_at:
            errors['ends_at'] = 'Дата окончания должна быть строго позже даты начала.'

        if self.workload is None:
            errors['workload'] = 'Укажите суммарную нагрузку.'
        elif self.workload < Decimal('0.5') or self.workload > Decimal('400.0'):
            errors['workload'] = 'Нагрузка должна быть от 0.5 до 400.0 часов.'

        if self.capacity is None or self.capacity < 1 or self.capacity > 500:
            errors['capacity'] = 'Число мест должно быть в диапазоне от 1 до 500.'

        if not self.reward_types or len(self.reward_types) == 0:
            errors['reward_types'] = 'Выберите хотя бы один вид поощрения.'
        else:
            if self.RewardType.NONE in self.reward_types and len(self.reward_types) > 1:
                errors['reward_types'] = 'Вид "Без вознаграждения" нельзя сочетать с другими видами поощрений.'

        if not self.reward_condition or not self.reward_condition.strip():
            errors['reward_condition'] = 'Укажите условие получения поощрения (например, "Футболка после окончания смены" или "Без вознаграждения").'

        if errors:
            raise ValidationError(errors)
