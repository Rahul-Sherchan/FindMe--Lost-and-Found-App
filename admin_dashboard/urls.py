from django.urls import path
from . import views

app_name = 'admin_dashboard'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('users/', views.manage_users, name='manage_users'),
    path('posts/', views.manage_posts, name='manage_posts'),
    path('claims/', views.manage_claims, name='manage_claims'),
    path('claims/<int:pk>/approve/', views.approve_claim, name='approve_claim'),
    path('claims/<int:pk>/reject/', views.reject_claim, name='reject_claim'),
    path('posts/<int:pk>/approve/', views.approve_item, name='approve_item'),
    path('posts/<int:pk>/delete/', views.delete_post, name='delete_post'),
    path('users/<int:pk>/toggle/', views.toggle_user_active, name='toggle_user_active'),
    path('users/<int:pk>/suspend/', views.suspend_user, name='suspend_user'),
    path('users/<int:pk>/', views.user_detail, name='user_detail'),
    path('calendar/', views.calendar_analytics, name='calendar_analytics'),
    path('api/calendar-data/', views.calendar_data_api, name='calendar_data_api'),
    path('api/calendar-month-data/', views.calendar_month_data_api, name='calendar_month_data_api'),
    path('announcements/', views.manage_announcements, name='manage_announcements'),
    path('announcements/<int:pk>/delete/', views.delete_announcement, name='delete_announcement'),
    path('profile/', views.admin_profile, name='admin_profile'),
    # Redeem Request Management
    path('redeem-requests/', views.manage_redeem_requests, name='manage_redeem_requests'),
    path('redeem-requests/<int:pk>/approve/', views.approve_redeem_request, name='approve_redeem_request'),
    path('redeem-requests/<int:pk>/reject/', views.reject_redeem_request, name='reject_redeem_request'),
    path('redeem-requests/<int:pk>/paid/', views.mark_redeem_paid, name='mark_redeem_paid'),
]
