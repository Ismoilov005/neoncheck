# Kahoot Mode URL patterns
from django.urls import path
from . import kahoot_views

urlpatterns = [
    # Guest Join
    path('join/', kahoot_views.kahoot_join, name='kahoot_join'),
    path('play/<str:pin>/lobby/', kahoot_views.kahoot_player_lobby, name='kahoot_player_lobby'),
    path('play/<str:pin>/game/', kahoot_views.kahoot_player_game, name='kahoot_player_game'),
    
    # Host (Admin)
    path('dashboard/', kahoot_views.kahoot_dashboard, name='kahoot_dashboard'),
    path('quiz/create/', kahoot_views.kahoot_create_quiz, name='kahoot_create_quiz'),
    path('quiz/<int:quiz_id>/edit/', kahoot_views.kahoot_edit_quiz, name='kahoot_edit_quiz'),
    path('question/<int:question_id>/edit/', kahoot_views.kahoot_edit_question, name='kahoot_edit_question'),
    path('question/<int:question_id>/delete/', kahoot_views.kahoot_delete_question, name='kahoot_delete_question'),
    path('quiz/<int:quiz_id>/start/', kahoot_views.kahoot_start_session, name='kahoot_start_session'),
    path('host/<str:pin>/lobby/', kahoot_views.kahoot_host_lobby, name='kahoot_host_lobby'),
    path('host/<str:pin>/game/', kahoot_views.kahoot_host_game, name='kahoot_host_game'),
    
    # API
    path('api/session/<str:pin>/', kahoot_views.kahoot_session_info, name='kahoot_session_info'),
]
