from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email обязателен для создания пользователя')
        email = self.normalize_email(email).strip().lower()
        extra_fields.setdefault('is_active', True)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('role', User.Role.MODERATOR)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('verified', True)
        extra_fields.setdefault('verified_at', timezone.now())
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        STUDENT = 'student', 'Студент'
        ORGANIZER = 'organizer', 'Организатор'
        MODERATOR = 'moderator', 'Модератор'

    email = models.EmailField('Email', max_length=254, unique=True, db_index=True)
    name = models.CharField('Имя и фамилия / Название организации', max_length=120)
    role = models.CharField('Роль', max_length=20, choices=Role.choices, default=Role.STUDENT)
    verified = models.BooleanField('Подтверждён модератором', default=False)
    verified_at = models.DateTimeField('Дата подтверждения', null=True, blank=True)

    is_active = models.BooleanField('Активен', default=True)
    is_staff = models.BooleanField('Доступ к административному интерфейсу', default=False)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['-created_at']

    def clean(self):
        super().clean()
        if self.email:
            self.email = self.email.strip().lower()

    def __str__(self):
        return f'{self.name} ({self.email}) [{self.get_role_display()}]'

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_organizer(self):
        return self.role == self.Role.ORGANIZER

    @property
    def is_moderator(self):
        return self.role == self.Role.MODERATOR
