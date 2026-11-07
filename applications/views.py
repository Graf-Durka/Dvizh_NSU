from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpResponseBadRequest, HttpResponseForbidden, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from opportunities.models import Opportunity
from .forms import ApplyForm
from .models import Application
from .services import (
    ApplicationServiceError,
    DuplicateApplicationError,
    EventAlreadyStartedError,
    NoSeatsLeftError,
    accept_application,
    apply_for_opportunity,
    cancel_application,
    complete_application,
    confirm_application,
    reject_application,
)


@login_required
def apply_view(request, opp_pk):
    if not request.user.is_student:
        return HttpResponseForbidden('Подавать заявки могут только студенты.')
    if request.method != 'POST':
        return HttpResponseBadRequest('Только POST метод.')

    opp = get_object_or_404(Opportunity, pk=opp_pk)
    form = ApplyForm(request.POST)

    if not form.is_valid():
        messages.error(request, 'Пожалуйста, заполните комментарий к заявке (до 500 символов).')
        return redirect('opportunities:detail', pk=opp.pk)

    comment = form.cleaned_data['comment']

    try:
        app = apply_for_opportunity(request.user, opp, comment)
        messages.success(request, f'Заявка на роль «{opp.title}» успешно отправлена! Организатор рассмотрит её в ближайшее время.')
        return redirect('applications:student_cabinet')
    except DuplicateApplicationError as e:
        existing = Application.objects.filter(opportunity=opp, student=request.user).first()
        return render(request, 'applications/conflict.html', {
            'title': 'Повторный отклик запрещён',
            'message': str(e),
            'opportunity': opp,
            'existing_application': existing,
        }, status=409)
    except NoSeatsLeftError as e:
        return render(request, 'applications/conflict.html', {
            'title': 'Свободных мест больше нет',
            'message': 'К сожалению, все свободные места на данную роль уже заняты подтверждёнными участниками.',
            'opportunity': opp,
        }, status=409)
    except ValidationError as e:
        messages.error(request, e.message if hasattr(e, 'message') else str(e))
        return redirect('opportunities:detail', pk=opp.pk)
    except ApplicationServiceError as e:
        messages.error(request, str(e))
        return redirect('opportunities:detail', pk=opp.pk)


@login_required
def confirm_view(request, app_pk):
    if not request.user.is_student:
        return HttpResponseForbidden('Подтверждать участие могут только студенты.')
    if request.method != 'POST':
        return HttpResponseBadRequest('Только POST метод.')

    app = get_object_or_404(Application.objects.select_related('opportunity'), pk=app_pk)

    try:
        confirm_application(request.user, app)
        messages.success(request, f'Вы подтвердили своё участие в роли «{app.opportunity.title}»! Место забронировано за вами.')
        return redirect('applications:student_cabinet')
    except NoSeatsLeftError:
        return render(request, 'applications/conflict.html', {
            'title': 'Все места уже заняты',
            'message': 'К сожалению, другие принятые участники подтвердили участие раньше, и лимит мест был исчерпан. Ваша заявка остаётся в статусе «Принята» — если кто-то отменит подтверждение, вы сможете занять освободившееся место.',
            'opportunity': app.opportunity,
            'existing_application': app,
        }, status=409)
    except (ValidationError, ApplicationServiceError) as e:
        messages.error(request, str(e))
        return redirect('applications:student_cabinet')


@login_required
def cancel_view(request, app_pk):
    if not request.user.is_student:
        return HttpResponseForbidden('Отменять свои заявки могут только студенты.')
    if request.method != 'POST':
        return HttpResponseBadRequest('Только POST метод.')

    app = get_object_or_404(Application.objects.select_related('opportunity'), pk=app_pk)

    try:
        cancel_application(request.user, app)
        messages.info(request, f'Заявка на роль «{app.opportunity.title}» была отменена. Место освобождено.')
    except (ValidationError, ApplicationServiceError) as e:
        messages.error(request, str(e))

    return redirect('applications:student_cabinet')


@login_required
def accept_view(request, app_pk):
    if not request.user.is_organizer:
        return HttpResponseForbidden('Принимать заявки могут только организаторы.')
    if request.method != 'POST':
        return HttpResponseBadRequest('Только POST метод.')

    app = get_object_or_404(Application.objects.select_related('opportunity'), pk=app_pk)

    try:
        accept_application(request.user, app)
        messages.success(request, f'Заявка студента {app.student.name} принята. Ожидайте подтверждения готовности от студента.')
    except (ValidationError, ApplicationServiceError) as e:
        messages.error(request, str(e))

    return redirect('applications:organizer_roster', opp_pk=app.opportunity_id)


@login_required
def reject_view(request, app_pk):
    if not request.user.is_organizer:
        return HttpResponseForbidden('Отклонять заявки могут только организаторы.')
    if request.method != 'POST':
        return HttpResponseBadRequest('Только POST метод.')

    app = get_object_or_404(Application.objects.select_related('opportunity'), pk=app_pk)

    try:
        reject_application(request.user, app)
        messages.info(request, f'Заявка студента {app.student.name} отклонена.')
    except (ValidationError, ApplicationServiceError) as e:
        messages.error(request, str(e))

    return redirect('applications:organizer_roster', opp_pk=app.opportunity_id)


@login_required
def complete_view(request, app_pk):
    if not request.user.is_organizer:
        return HttpResponseForbidden('Отмечать выполнение могут только организаторы.')
    if request.method != 'POST':
        return HttpResponseBadRequest('Только POST метод.')

    app = get_object_or_404(Application.objects.select_related('opportunity'), pk=app_pk)

    try:
        complete_application(request.user, app)
        messages.success(request, f'Выполнение роли студентом {app.student.name} успешно зафиксировано!')
    except (ValidationError, ApplicationServiceError) as e:
        messages.error(request, str(e))

    return redirect('applications:organizer_roster', opp_pk=app.opportunity_id)


@login_required
def student_cabinet_view(request):
    if not request.user.is_student:
        return HttpResponseForbidden('Личный кабинет заявок доступен только студентам.')

    applications = Application.objects.filter(student=request.user).select_related(
        'opportunity', 'opportunity__organizer'
    ).prefetch_related('events', 'events__actor').order_by('-created_at')

    return render(request, 'applications/student_cabinet.html', {
        'applications': applications,
        'now': timezone.now(),
    })


@login_required
def organizer_roster_view(request, opp_pk):
    if not request.user.is_organizer:
        return HttpResponseForbidden('Доступ только для организаторов.')

    opp = get_object_or_404(Opportunity, pk=opp_pk)
    if opp.organizer_id != request.user.id:
        return HttpResponseForbidden('Вы не являетесь организатором этого набора.')

    status_filter = request.GET.get('status', '').strip()
    apps_qs = opp.applications.select_related('student').prefetch_related('events').order_by('-created_at')
    if status_filter:
        apps_qs = apps_qs.filter(status=status_filter)

    return render(request, 'applications/organizer_roster.html', {
        'opportunity': opp,
        'applications': apps_qs,
        'selected_status': status_filter,
        'statuses': Application.Status.choices,
        'now': timezone.now(),
    })
