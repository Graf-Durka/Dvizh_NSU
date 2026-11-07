from django.urls import path
from . import views

app_name = 'applications'

urlpatterns = [
    # Кабинет студента
    path('cabinet/student/', views.student_cabinet_view, name='student_cabinet'),
    path('applications/my/', views.student_cabinet_view, name='my_applications_alias'),

    # Отклик на возможность (F3)
    path('opportunities/<int:opp_pk>/apply/', views.apply_view, name='apply'),

    # Действия студента по заявке
    path('applications/<int:app_pk>/confirm/', views.confirm_view, name='confirm'),
    path('applications/<int:app_pk>/cancel/', views.cancel_view, name='cancel'),

    # Действия организатора по заявкам
    path('organizer/cards/<int:opp_pk>/applications/', views.organizer_roster_view, name='organizer_roster'),
    path('applications/<int:app_pk>/accept/', views.accept_view, name='accept'),
    path('applications/<int:app_pk>/reject/', views.reject_view, name='reject'),
    path('applications/<int:app_pk>/complete/', views.complete_view, name='complete'),
]
