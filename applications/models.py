from django.conf import settings
from django.db import models


class Application(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Отправлена'
        ACCEPTED = 'ACCEPTED', 'Принята'
        REJECTED = 'REJECTED', 'Отклонена'
        CONFIRMED = 'CONFIRMED', 'Подтверждена'
        CANCELLED = 'CANCELLED', 'Отменена'
        COMPLETED = 'COMPLETED', 'Выполнена'

    opportunity = models.ForeignKey(
        'opportunities.Opportunity',
        on_delete=models.CASCADE,
        related_name='applications',
        verbose_name='Возможность'
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='applications',
        verbose_name='Студент'
    )
    comment = models.TextField('Комментарий студента', max_length=500)
    status = models.CharField(
        'Статус заявки',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )
    decided_at = models.DateTimeField('Дата решения организатора', null=True, blank=True)
    confirmed_at = models.DateTimeField('Дата подтверждения студентом', null=True, blank=True)

    created_at = models.DateTimeField('Дата подачи', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)

    class Meta:
        verbose_name = 'Заявка'
        verbose_name_plural = 'Заявки'
        unique_together = ('opportunity', 'student')
        ordering = ['-created_at']

    def __str__(self):
        return f'Заявка #{self.id} от {self.student.name} на "{self.opportunity.title}" ({self.get_status_display()})'

    @property
    def occupies_seat(self):
        return self.status in [self.Status.CONFIRMED, self.Status.COMPLETED]


class ApplicationEvent(models.Model):
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='events',
        verbose_name='Заявка'
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Инициатор изменения'
    )
    from_status = models.CharField('Из статуса', max_length=20, null=True, blank=True)
    to_status = models.CharField('В статус', max_length=20)
    created_at = models.DateTimeField('Время события', auto_now_add=True)

    class Meta:
        verbose_name = 'Событие заявки'
        verbose_name_plural = 'События заявки'
        ordering = ['created_at']

    def __str__(self):
        from_st = self.from_status or 'Создание'
        return f'{self.created_at:%d.%m.%Y %H:%M} [{from_st} → {self.to_status}] ({self.actor.name})'
