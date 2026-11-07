from decimal import Decimal
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Opportunity


class OpportunityForm(forms.ModelForm):
    reward_types = forms.MultipleChoiceField(
        choices=Opportunity.RewardType.choices,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        label='Виды поощрения',
        required=False
    )

    class Meta:
        model = Opportunity
        fields = [
            'category', 'title', 'duties', 'starts_at', 'ends_at', 'deadline',
            'location', 'workload', 'skills', 'capacity', 'reward_types', 'reward_condition'
        ]
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Например: Помощь на регистрации участников конференции'}),
            'duties': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Опишите конкретные задачи и обязанности...'}),
            'starts_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'ends_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'deadline': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Главный корпус НГУ, ауд. 3107'}),
            'workload': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5', 'placeholder': '4.0'}),
            'skills': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Опыт не требуется / Базовый Python / Грамотная речь'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 500}),
            'reward_condition': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Например: Питание и футболка после завершения смены'}),
        }

    def __init__(self, *args, is_restricted=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_restricted = is_restricted
        if self.instance and self.instance.pk:
            self.initial['reward_types'] = self.instance.reward_types

        # Если уже есть отклики, условия менять нельзя — только увеличивать число мест
        if is_restricted:
            restricted_fields = [
                'category', 'title', 'duties', 'starts_at', 'ends_at', 'deadline',
                'location', 'workload', 'skills', 'reward_types', 'reward_condition'
            ]
            for f in restricted_fields:
                self.fields[f].disabled = True
                self.fields[f].required = False

    def clean_title(self):
        title = self.cleaned_data.get('title', '').strip()
        if len(title) > 120:
            raise ValidationError('Название роли не должно превышать 120 символов.')
        return title

    def clean_duties(self):
        duties = self.cleaned_data.get('duties', '').strip()
        if len(duties) > 2000:
            raise ValidationError('Обязанности не должны превышать 2000 символов.')
        return duties

    def clean_location(self):
        loc = self.cleaned_data.get('location', '').strip()
        if len(loc) > 200:
            raise ValidationError('Место проведения не должно превышать 200 символов.')
        return loc

    def clean_skills(self):
        skills = self.cleaned_data.get('skills', '').strip()
        if len(skills) > 500:
            raise ValidationError('Требуемые навыки не должны превышать 500 символов.')
        return skills

    def clean_reward_condition(self):
        cond = self.cleaned_data.get('reward_condition', '').strip()
        if len(cond) > 500:
            raise ValidationError('Условие получения поощрения не должно превышать 500 символов.')
        return cond

    def clean_capacity(self):
        cap = self.cleaned_data.get('capacity')
        if cap is not None:
            if cap < 1 or cap > 500:
                raise ValidationError('Число мест должно быть в диапазоне от 1 до 500.')
            if self.is_restricted and self.instance and self.instance.pk:
                occupied = self.instance.occupied_seats
                if cap < occupied:
                    raise ValidationError(f'Нельзя уменьшить число мест меньше уже занятых ({occupied}).')
        return cap

    def clean_workload(self):
        wl = self.cleaned_data.get('workload')
        if wl is not None:
            if wl < Decimal('0.5') or wl > Decimal('400.0'):
                raise ValidationError('Нагрузка должна быть от 0.5 до 400.0 часов.')
        return wl

    def clean(self):
        cleaned_data = super().clean()
        if self.is_restricted:
            return cleaned_data

        rtypes = cleaned_data.get('reward_types') or []
        if Opportunity.RewardType.NONE in rtypes and len(rtypes) > 1:
            self.add_error('reward_types', 'Вид "Без вознаграждения" нельзя сочетать с другими видами поощрений.')

        deadline = cleaned_data.get('deadline')
        starts_at = cleaned_data.get('starts_at')
        ends_at = cleaned_data.get('ends_at')

        if deadline and starts_at and starts_at < deadline:
            self.add_error('starts_at', 'Дата начала не может быть раньше срока отклика.')

        if starts_at and ends_at and ends_at <= starts_at:
            self.add_error('ends_at', 'Дата окончания должна быть строго позже даты начала.')

        return cleaned_data


class ModerationReturnForm(forms.Form):
    moderation_note = forms.CharField(
        label='Причина возврата на доработку',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Укажите конкретную причину возврата, чтобы автор мог исправить карточку...'
        }),
        max_length=500,
        required=True
    )
