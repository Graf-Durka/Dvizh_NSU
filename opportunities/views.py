from datetime import datetime
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.http import HttpResponseBadRequest, HttpResponseForbidden, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .forms import ModerationReturnForm, OpportunityForm
from .models import Opportunity


def catalog_view(request):
    category = request.GET.get('category', '').strip()
    date_from_str = request.GET.get('date_from', '').strip()
    date_to_str = request.GET.get('date_to', '').strip()
    workload_filter = request.GET.get('workload', '').strip()
    reward_filter = request.GET.get('reward', '').strip()

    # Валидация входных фильтров (по ТЗ: невалидный enum/диапазон -> 400)
    valid_categories = [c[0] for c in Opportunity.Category.choices]
    if category and category not in valid_categories:
        return HttpResponseBadRequest('Недопустимая категория.')

    valid_rewards = [r[0] for r in Opportunity.RewardType.choices]
    if reward_filter and reward_filter not in valid_rewards:
        return HttpResponseBadRequest('Недопустимый вид поощрения.')

    valid_workloads = ['le2', '2to4', 'gt4']
    if workload_filter and workload_filter not in valid_workloads:
        return HttpResponseBadRequest('Недопустимый диапазон нагрузки.')

    date_from = None
    date_to = None
    if date_from_str:
        try:
            date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date()
        except ValueError:
            return HttpResponseBadRequest('Неверный формат даты начала.')

    if date_to_str:
        try:
            date_to = datetime.strptime(date_to_str, '%Y-%m-%d').date()
        except ValueError:
            return HttpResponseBadRequest('Неверный формат даты окончания.')

    if date_from and date_to and date_to < date_from:
        return HttpResponseBadRequest('Дата окончания диапазона не может быть раньше даты начала.')

    # Базовый набор: только опубликованные с неистёкшим дедлайном
    now = timezone.now()
    qs = Opportunity.objects.filter(
        status=Opportunity.Status.PUBLISHED,
        deadline__gt=now
    ).select_related('organizer').order_by('starts_at')

    # Применение фильтров (объединяются по И)
    if category:
        qs = qs.filter(category=category)

    if date_from:
        qs = qs.filter(starts_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(starts_at__date__lte=date_to)

    if workload_filter == 'le2':
        qs = qs.filter(workload__lte=2.0)
    elif workload_filter == '2to4':
        qs = qs.filter(workload__gt=2.0, workload__lte=4.0)
    elif workload_filter == 'gt4':
        qs = qs.filter(workload__gt=4.0)

    # Вид поощрения: проверяем наличие значения в JSONField
    if reward_filter:
        qs = qs.filter(reward_types__icontains=f'"{reward_filter}"')

    # Пагинация: 12 карточек на страницу
    paginator = Paginator(qs, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'categories': Opportunity.Category.choices,
        'reward_types': Opportunity.RewardType.choices,
        'selected_category': category,
        'selected_reward': reward_filter,
        'selected_workload': workload_filter,
        'date_from': date_from_str,
        'date_to': date_to_str,
    }
    return render(request, 'opportunities/catalog.html', context)


def detail_view(request, pk):
    opp = get_object_or_404(Opportunity.objects.select_related('organizer', 'reviewed_by'), pk=pk)

    # Проверка прав доступа к черновикам и непроверенным карточкам
    if opp.status in [Opportunity.Status.DRAFT, Opportunity.Status.PENDING_REVIEW]:
        if not request.user.is_authenticated:
            raise Http404('Объявление не найдено.')
        is_owner = (opp.organizer_id == request.user.id)
        is_mod = request.user.is_moderator
        if not (is_owner or is_mod):
            raise Http404('Объявление не найдено.')

    # Проверяем, подавал ли текущий студент заявку
    existing_application = None
    if request.user.is_authenticated and request.user.is_student:
        existing_application = opp.applications.filter(student=request.user).first()

    return render(request, 'opportunities/detail.html', {
        'opportunity': opp,
        'existing_application': existing_application,
        'now': timezone.now(),
    })


@login_required
def organizer_cards_view(request):
    if not request.user.is_organizer:
        return HttpResponseForbidden('Доступ только для организаторов.')

    cards = Opportunity.objects.filter(organizer=request.user).prefetch_related('applications').order_by('-created_at')
    return render(request, 'opportunities/organizer_cards.html', {'cards': cards})


@login_required
def create_opportunity_view(request):
    if not request.user.is_organizer:
        return HttpResponseForbidden('Доступ только для организаторов.')

    if request.method == 'POST':
        action = request.POST.get('action', 'save_draft')
        form = OpportunityForm(request.POST)

        if action == 'save_draft':
            # В черновике разрешены неполные данные
            if form.is_valid():
                opp = form.save(commit=False)
                opp.organizer = request.user
                opp.status = Opportunity.Status.DRAFT
                opp.reward_types = form.cleaned_data.get('reward_types') or []
                opp.save()
                messages.success(request, 'Черновик роли успешно сохранён.')
                return redirect('opportunities:organizer_cards')
        else:
            # Публикация / отправка на проверку
            if form.is_valid():
                opp = form.save(commit=False)
                opp.organizer = request.user
                opp.reward_types = form.cleaned_data.get('reward_types') or []

                try:
                    opp.validate_for_publication()
                except ValidationError as e:
                    for field, errs in e.message_dict.items():
                        for err in errs:
                            form.add_error(field if field in form.fields else None, err)
                    return render(request, 'opportunities/form.html', {'form': form, 'is_new': True})

                if not request.user.verified:
                    # Проверяем, есть ли уже карточка на проверке
                    has_pending = Opportunity.objects.filter(
                        organizer=request.user,
                        status=Opportunity.Status.PENDING_REVIEW
                    ).exists()
                    if has_pending:
                        messages.error(request, 'У вас уже есть одна карточка на проверке у модератора. Дождитесь её одобрения.')
                        return render(request, 'opportunities/form.html', {'form': form, 'is_new': True})

                    opp.status = Opportunity.Status.PENDING_REVIEW
                    opp.save()
                    messages.info(request, 'Карточка отправлена на первичную модерацию. После её одобрения ваш аккаунт будет подтверждён.')
                else:
                    opp.status = Opportunity.Status.PUBLISHED
                    opp.published_at = timezone.now()
                    opp.save()
                    messages.success(request, 'Карточка успешно опубликована в каталоге!')

                return redirect('opportunities:organizer_cards')
    else:
        form = OpportunityForm()

    return render(request, 'opportunities/form.html', {'form': form, 'is_new': True})


@login_required
def edit_opportunity_view(request, pk):
    opp = get_object_or_404(Opportunity, pk=pk)

    if opp.organizer_id != request.user.id:
        return HttpResponseForbidden('Вы не можете редактировать чужую карточку.')

    if opp.status == Opportunity.Status.PENDING_REVIEW:
        messages.warning(request, 'Карточка находится на проверке. Для редактирования сначала отзовите её с проверки.')
        return redirect('opportunities:organizer_cards')

    if opp.status == Opportunity.Status.CLOSED:
        messages.error(request, 'Закрытый набор нельзя редактировать.')
        return redirect('opportunities:organizer_cards')

    is_restricted = opp.has_applications

    if request.method == 'POST':
        action = request.POST.get('action', 'save')
        form = OpportunityForm(request.POST, instance=opp, is_restricted=is_restricted)

        if form.is_valid():
            opp = form.save(commit=False)
            if not is_restricted:
                opp.reward_types = form.cleaned_data.get('reward_types') or []

            if action == 'publish' and opp.status == Opportunity.Status.DRAFT:
                try:
                    opp.validate_for_publication()
                except ValidationError as e:
                    for field, errs in e.message_dict.items():
                        for err in errs:
                            form.add_error(field if field in form.fields else None, err)
                    return render(request, 'opportunities/form.html', {'form': form, 'opportunity': opp, 'is_restricted': is_restricted})

                if not request.user.verified:
                    has_pending = Opportunity.objects.filter(
                        organizer=request.user,
                        status=Opportunity.Status.PENDING_REVIEW
                    ).exclude(pk=opp.pk).exists()
                    if has_pending:
                        messages.error(request, 'У вас уже есть карточка на проверке.')
                        return render(request, 'opportunities/form.html', {'form': form, 'opportunity': opp, 'is_restricted': is_restricted})
                    opp.status = Opportunity.Status.PENDING_REVIEW
                    opp.save()
                    messages.info(request, 'Карточка отправлена на проверку модератору.')
                else:
                    opp.status = Opportunity.Status.PUBLISHED
                    opp.published_at = timezone.now()
                    opp.save()
                    messages.success(request, 'Карточка опубликована!')
            else:
                opp.save()
                messages.success(request, 'Изменения сохранены.')

            return redirect('opportunities:organizer_cards')
    else:
        form = OpportunityForm(instance=opp, is_restricted=is_restricted)

    return render(request, 'opportunities/form.html', {
        'form': form,
        'opportunity': opp,
        'is_restricted': is_restricted
    })


@login_required
def close_opportunity_view(request, pk):
    if request.method != 'POST':
        return HttpResponseBadRequest('Только POST метод.')

    opp = get_object_or_404(Opportunity, pk=pk)
    if opp.organizer_id != request.user.id:
        return HttpResponseForbidden('Вы не можете закрыть чужую карточку.')

    if opp.status == Opportunity.Status.CLOSED:
        messages.info(request, 'Набор уже был закрыт ранее.')
    else:
        opp.status = Opportunity.Status.CLOSED
        opp.closed_at = timezone.now()
        opp.save(update_fields=['status', 'closed_at', 'updated_at'])
        messages.success(request, f'Набор на роль «{opp.title}» успешно закрыт. Карточка убрана из активного каталога.')

    return redirect('opportunities:organizer_cards')


@login_required
def withdraw_opportunity_view(request, pk):
    if request.method != 'POST':
        return HttpResponseBadRequest('Только POST метод.')

    opp = get_object_or_404(Opportunity, pk=pk)
    if opp.organizer_id != request.user.id:
        return HttpResponseForbidden('Вы не можете отозвать чужую карточку.')

    if opp.status == Opportunity.Status.PENDING_REVIEW:
        opp.status = Opportunity.Status.DRAFT
        opp.save(update_fields=['status', 'updated_at'])
        messages.info(request, 'Карточка отозвана с проверки и возвращена в черновики.')
    else:
        messages.warning(request, 'Карточка не находится на проверке.')

    return redirect('opportunities:organizer_cards')


@login_required
def moderation_queue_view(request):
    if not request.user.is_moderator:
        return HttpResponseForbidden('Доступ только для модераторов.')

    pending_cards = Opportunity.objects.filter(
        status=Opportunity.Status.PENDING_REVIEW
    ).select_related('organizer').order_by('created_at')

    return render(request, 'opportunities/moderation_queue.html', {'pending_cards': pending_cards})


@login_required
def moderation_approve_view(request, pk):
    if not request.user.is_moderator:
        return HttpResponseForbidden('Доступ только для модераторов.')
    if request.method != 'POST':
        return HttpResponseBadRequest('Только POST метод.')

    with transaction.atomic():
        opp = get_object_or_404(
            Opportunity.objects.select_for_update().select_related('organizer'),
            pk=pk,
            status=Opportunity.Status.PENDING_REVIEW
        )

        # Проверка срока отклика: просроченную нельзя публиковать
        if opp.deadline and opp.deadline <= timezone.now():
            opp.status = Opportunity.Status.DRAFT
            opp.moderation_note = 'Срок отклика истёк до момента проверки. Обновите даты.'
            opp.reviewed_by = request.user
            opp.save()
            messages.error(request, 'Карточка возвращена в черновики: срок отклика уже истёк.')
            return redirect('opportunities:moderation_queue')

        # Одобрение карточки и подтверждение организатора
        opp.status = Opportunity.Status.PUBLISHED
        opp.published_at = timezone.now()
        opp.reviewed_by = request.user
        opp.moderation_note = ''
        opp.save()

        organizer = opp.organizer
        organizer.verified = True
        organizer.verified_at = timezone.now()
        organizer.save(update_fields=['verified', 'verified_at'])

    messages.success(request, f'Карточка «{opp.title}» одобрена и опубликована. Организатор {organizer.name} подтверждён!')
    return redirect('opportunities:moderation_queue')


@login_required
def moderation_return_view(request, pk):
    if not request.user.is_moderator:
        return HttpResponseForbidden('Доступ только для модераторов.')
    if request.method != 'POST':
        return HttpResponseBadRequest('Только POST метод.')

    opp = get_object_or_404(Opportunity, pk=pk, status=Opportunity.Status.PENDING_REVIEW)
    form = ModerationReturnForm(request.POST)

    if form.is_valid():
        note = form.cleaned_data['moderation_note']
        opp.status = Opportunity.Status.DRAFT
        opp.moderation_note = note
        opp.reviewed_by = request.user
        opp.save(update_fields=['status', 'moderation_note', 'reviewed_by', 'updated_at'])
        messages.info(request, f'Карточка «{opp.title}» возвращена автору на доработку с указанием причины.')
    else:
        messages.error(request, 'Укажите обязательную причину возврата.')

    return redirect('opportunities:moderation_queue')
