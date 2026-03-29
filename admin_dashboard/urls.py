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
    path('reports/', views.reports, name='reports'),
]
