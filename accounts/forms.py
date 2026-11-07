from django import forms
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from .models import User


class UserRegistrationForm(forms.ModelForm):
    ROLE_CHOICES = [
        (User.Role.STUDENT, 'Студент'),
        (User.Role.ORGANIZER, 'Организатор / Лаборатория'),
    ]

    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        label='Тип учётной записи',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Минимум 6 символов'}),
        min_length=6
    )
    password_confirm = forms.CharField(
        label='Повторите пароль',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Повторите пароль'})
    )

    class Meta:
        model = User
        fields = ['name', 'email', 'role', 'password']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Иван Иванов или Лаборатория ИИ'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'name@nsu.ru'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email=email).exists():
            raise ValidationError('Пользователь с таким email уже зарегистрирован.')
        return email

    def clean_role(self):
        role = self.cleaned_data.get('role')
        if role not in [User.Role.STUDENT, User.Role.ORGANIZER]:
            raise ValidationError('Недопустимая роль пользователя.')
        return role

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('password_confirm')
        if p1 and p2 and p1 != p2:
            self.add_error('password_confirm', 'Пароли не совпадают.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email'].strip().lower()
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class UserLoginForm(forms.Form):
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'name@nsu.ru', 'autofocus': True})
    )
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Пароль'})
    )

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email', '').strip().lower()
        password = cleaned_data.get('password')
        if email and password:
            user = authenticate(username=email, password=password)
            if not user:
                raise ValidationError('Неверный email или пароль.')
            if not user.is_active:
                raise ValidationError('Учётная запись деактивирована.')
            self.user = user
        return cleaned_data
