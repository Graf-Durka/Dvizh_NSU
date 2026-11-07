from django.urls import path
from . import views

app_name = 'opportunities'

urlpatterns = [
    # Каталог и карточка (F2)
    path('', views.catalog_view, name='catalog'),
    path('opportunities/', views.catalog_view, name='catalog_alias'),
    path('opportunities/<int:pk>/', views.detail_view, name='detail'),

    # Кабинет организатора (F1)
    path('organizer/cards/', views.organizer_cards_view, name='organizer_cards'),
    path('organizer/cards/new/', views.create_opportunity_view, name='create_opportunity'),
    path('organizer/cards/<int:pk>/edit/', views.edit_opportunity_view, name='edit_opportunity'),
    path('organizer/cards/<int:pk>/close/', views.close_opportunity_view, name='close_opportunity'),
    path('organizer/cards/<int:pk>/withdraw/', views.withdraw_opportunity_view, name='withdraw_opportunity'),

    # Кабинет модератора
    path('moderation/', views.moderation_queue_view, name='moderation_queue'),
    path('moderation/<int:pk>/approve/', views.moderation_approve_view, name='moderation_approve'),
    path('moderation/<int:pk>/return/', views.moderation_return_view, name='moderation_return'),
]
