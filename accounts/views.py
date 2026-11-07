from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from .forms import UserLoginForm, UserRegistrationForm
from .models import User


def register_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:cabinet')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Добро пожаловать в «Движ НГУ», {user.name}!')
            return redirect('accounts:cabinet')
    else:
        form = UserRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:cabinet')

    next_url = request.GET.get('next', '')

    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            user = form.user
            login(request, user)
            messages.success(request, f'С возвращением, {user.name}!')
            post_next = request.POST.get('next', '')
            if post_next and url_has_allowed_host_and_scheme(post_next, allowed_hosts={request.get_host()}):
                return redirect(post_next)
            return redirect('accounts:cabinet')
    else:
        form = UserLoginForm()

    return render(request, 'accounts/login.html', {'form': form, 'next': next_url})


def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.info(request, 'Вы успешно вышли из аккаунта.')
    return redirect('opportunities:catalog')


@login_required
def cabinet_redirect_view(request):
    if request.user.role == User.Role.STUDENT:
        return redirect('applications:student_cabinet')
    elif request.user.role == User.Role.ORGANIZER:
        return redirect('opportunities:organizer_cards')
    elif request.user.role == User.Role.MODERATOR:
        return redirect('opportunities:moderation_queue')
    return redirect('opportunities:catalog')
