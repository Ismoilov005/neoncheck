from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Authentication
    path('login/', auth_views.LoginView.as_view(template_name='quizzes/login.html'), name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # Main pages
    path('', views.index, name='index'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # Superuser routes
    path('superuser/', views.superuser_dashboard, name='superuser_dashboard'),
    path('manage-users/', views.manage_users, name='manage_users'),

    # Admin routes
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('test/create/', views.test_create, name='test_create'),
    path('test/<int:test_id>/edit/', views.test_edit, name='test_edit'),
    path('test/<int:test_id>/delete/', views.test_delete, name='test_delete'),
    path('test/<int:test_id>/question/add/', views.question_add, name='question_add'),
    path('test/<int:test_id>/questions/bulk-upload/', views.bulk_upload_questions, name='bulk_upload_questions'),
    path('question/<int:question_id>/delete/', views.question_delete, name='question_delete'),
    path('test/<int:test_id>/results/', views.test_results, name='test_results'),

    # User routes
    path('user-dashboard/', views.user_dashboard, name='user_dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('notifications/', views.notifications_list, name='notifications_list'),
    path('notification/<int:notification_id>/read/', views.notification_mark_read, name='notification_mark_read'),
    path('test/<int:test_id>/take/', views.test_take, name='test_take'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('certificate/<int:result_id>/', views.certificate_show, name='certificate_show'),
    path('certificate/<int:result_id>/download/', views.download_certificate, name='download_certificate'),
    # Superuser exclusive (is_superuser)
    path('superuser/certificates/', views.superuser_certificates, name='superuser_certificates'),
    path('superuser/send-notification-all/', views.superuser_send_notification_all, name='superuser_send_notification_all'),

    # AJAX endpoints
    path('api/check-answer/', views.check_answer, name='check_answer'),
    path('test/<int:test_id>/submit/', views.submit_test, name='submit_test'),
    path('api/user/<int:user_id>/toggle-role/', views.toggle_user_role, name='toggle_user_role'),
]
