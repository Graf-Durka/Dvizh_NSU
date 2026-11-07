from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from opportunities.models import Opportunity
from .models import Application, ApplicationEvent


class ApplicationServiceError(Exception):
    pass


class DuplicateApplicationError(ApplicationServiceError):
    pass


class NoSeatsLeftError(ApplicationServiceError):
    pass


class EventAlreadyStartedError(ApplicationServiceError):
    pass


def apply_for_opportunity(student, opportunity, comment):
    """
    Подача студентом заявки на участие в роли.
    Проверяет сессию студента, активность карточки, дедлайн, свободные места и отсутствие повтора.
    """
    if not student.is_authenticated or not student.is_student:
        raise ValidationError('Только зарегистрированные студенты могут подавать заявки.')

    if opportunity.status != Opportunity.Status.PUBLISHED:
        raise ValidationError('Набор на эту роль не принимает заявки (не опубликован).')

    now = timezone.now()
    if opportunity.deadline and opportunity.deadline <= now:
        raise ValidationError('Срок отклика на данную роль уже истёк.')

    # Проверка уникальности отклика
    if Application.objects.filter(opportunity=opportunity, student=student).exists():
        existing = Application.objects.filter(opportunity=opportunity, student=student).first()
        raise DuplicateApplicationError(f'Вы уже подавали заявку на эту роль (статус: {existing.get_status_display()}).')

    if opportunity.free_seats <= 0:
        raise NoSeatsLeftError('Свободных мест больше нет.')

    with transaction.atomic():
        app = Application.objects.create(
            opportunity=opportunity,
            student=student,
            comment=comment.strip(),
            status=Application.Status.PENDING
        )
        ApplicationEvent.objects.create(
            application=app,
            actor=student,
            from_status=None,
            to_status=Application.Status.PENDING
        )

    return app


def accept_application(organizer, application):
    """
    Организатор принимает поданную заявку (до начала события).
    ВАЖНО: Принятие не занимает место — место резервируется только после подтверждения студентом!
    """
    opp = application.opportunity
    if opp.organizer_id != organizer.id:
        raise ValidationError('Недостаточно прав: вы не являетесь организатором этой карточки.')

    now = timezone.now()
    if opp.starts_at and opp.starts_at <= now:
        raise EventAlreadyStartedError('Нельзя изменить статус заявки: событие уже началось.')

    if application.status != Application.Status.PENDING:
        raise ValidationError(f'Нельзя принять заявку в статусе «{application.get_status_display()}».')

    with transaction.atomic():
        old_status = application.status
        application.status = Application.Status.ACCEPTED
        application.decided_at = now
        application.save(update_fields=['status', 'decided_at', 'updated_at'])

        ApplicationEvent.objects.create(
            application=application,
            actor=organizer,
            from_status=old_status,
            to_status=Application.Status.ACCEPTED
        )

    return application


def reject_application(organizer, application):
    """Организатор отклоняет поданную заявку (до начала события)."""
    opp = application.opportunity
    if opp.organizer_id != organizer.id:
        raise ValidationError('Недостаточно прав: вы не являетесь организатором этой карточки.')

    now = timezone.now()
    if opp.starts_at and opp.starts_at <= now:
        raise EventAlreadyStartedError('Нельзя отклонить заявку: событие уже началось.')

    if application.status not in [Application.Status.PENDING, Application.Status.ACCEPTED]:
        raise ValidationError(f'Нельзя отклонить заявку в статусе «{application.get_status_display()}».')

    with transaction.atomic():
        old_status = application.status
        application.status = Application.Status.REJECTED
        application.decided_at = now
        application.save(update_fields=['status', 'decided_at', 'updated_at'])

        ApplicationEvent.objects.create(
            application=application,
            actor=organizer,
            from_status=old_status,
            to_status=Application.Status.REJECTED
        )

    return application


def confirm_application(student, application):
    """
    Студент подтверждает принятую заявку (до начала события).
    Выполняется в транзакции с блокировкой карточки (select_for_update),
    чтобы гарантировать строгое соблюдение лимита мест даже при одновременных подтверждениях.
    """
    if application.student_id != student.id:
        raise ValidationError('Вы можете подтверждать только свои собственные заявки.')

    now = timezone.now()
    if application.status != Application.Status.ACCEPTED:
        raise ValidationError(f'Подтвердить можно только принятую организатором заявку. Текущий статус: «{application.get_status_display()}».')

    with transaction.atomic():
        # Блокируем сначала карточку возможности
        locked_opp = Opportunity.objects.select_for_update().get(pk=application.opportunity_id)

        # Проверяем дату начала события
        if locked_opp.starts_at and locked_opp.starts_at <= now:
            raise EventAlreadyStartedError('Событие уже началось. Подтверждение участия невозможно.')

        # Блокируем заявку
        locked_app = Application.objects.select_for_update().get(pk=application.id)
        if locked_app.status != Application.Status.ACCEPTED:
            raise ValidationError('Статус заявки был изменён в параллельном запросе.')

        # Пересчитываем занятые места (подтверждённые + выполненные)
        occupied_seats = Application.objects.filter(
            opportunity=locked_opp,
            status__in=[Application.Status.CONFIRMED, Application.Status.COMPLETED]
        ).count()

        if occupied_seats >= locked_opp.capacity:
            raise NoSeatsLeftError('Все доступные места уже заняты другими участниками.')

        old_status = locked_app.status
        locked_app.status = Application.Status.CONFIRMED
        locked_app.confirmed_at = now
        locked_app.save(update_fields=['status', 'confirmed_at', 'updated_at'])

        ApplicationEvent.objects.create(
            application=locked_app,
            actor=student,
            from_status=old_status,
            to_status=Application.Status.CONFIRMED
        )

    return locked_app


def cancel_application(student, application):
    """
    Студент отзывает или отменяет подтверждение до начала события.
    Отмена подтверждённой заявки освобождает место.
    """
    if application.student_id != student.id:
        raise ValidationError('Вы можете отменять только свои собственные заявки.')

    opp = application.opportunity
    now = timezone.now()
    if opp.starts_at and opp.starts_at <= now:
        raise EventAlreadyStartedError('Событие уже началось. Отменить заявку нельзя.')

    if application.status not in [Application.Status.PENDING, Application.Status.ACCEPTED, Application.Status.CONFIRMED]:
        raise ValidationError(f'Нельзя отменить заявку в статусе «{application.get_status_display()}».')

    with transaction.atomic():
        # Блокируем карточку и заявку
        locked_opp = Opportunity.objects.select_for_update().get(pk=opp.pk)
        locked_app = Application.objects.select_for_update().get(pk=application.pk)

        old_status = locked_app.status
        locked_app.status = Application.Status.CANCELLED
        locked_app.save(update_fields=['status', 'updated_at'])

        ApplicationEvent.objects.create(
            application=locked_app,
            actor=student,
            from_status=old_status,
            to_status=Application.Status.CANCELLED
        )

    return locked_app


def complete_application(organizer, application):
    """
    Организатор отмечает фактическое выполнение роли студентом.
    Условия:
    1. Карточка закрыта (status == CLOSED)
    2. Событие завершилось (ends_at <= now)
    3. Заявка была подтверждена (status == CONFIRMED)
    """
    opp = application.opportunity
    if opp.organizer_id != organizer.id:
        raise ValidationError('Недостаточно прав: вы не являетесь организатором этой карточки.')

    if opp.status != Opportunity.Status.CLOSED:
        raise ValidationError('Отметку о выполнении можно поставить только после официального закрытия набора.')

    now = timezone.now()
    if opp.ends_at and opp.ends_at > now:
        raise ValidationError('Событие ещё не завершилось. Отметку можно поставить только после окончания события.')

    if application.status != Application.Status.CONFIRMED:
        raise ValidationError(f'Отметить выполнение можно только для подтверждённой заявки. Текущий статус: «{application.get_status_display()}».')

    with transaction.atomic():
        old_status = application.status
        application.status = Application.Status.COMPLETED
        application.save(update_fields=['status', 'updated_at'])

        ApplicationEvent.objects.create(
            application=application,
            actor=organizer,
            from_status=old_status,
            to_status=Application.Status.COMPLETED
        )

    return application
