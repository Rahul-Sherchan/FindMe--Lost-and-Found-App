from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('upgrade-premium/', views.upgrade_to_premium, name='upgrade_premium'),
    path('points-history/', views.points_history, name='points_history'),
    # Password reset (forgot password) flow
    path('password-reset/', views.password_reset_request, name='password_reset'),
    path('password-reset/done/', views.password_reset_done, name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', views.password_reset_confirm, name='password_reset_confirm'),
    path('password-reset/complete/', views.password_reset_complete, name='password_reset_complete'),
    
    # Khalti v1 widget: JS popup → token → verify backend
    path('khalti-verify/',   views.khalti_verify,   name='khalti_verify'),
    path('khalti-success/',  views.khalti_success,  name='khalti_success'),

    # Khalti ePay v2 (server-side redirect flow — kept as backup)
    path('khalti-initiate/', views.khalti_initiate, name='khalti_initiate'),
    path('khalti-callback/', views.khalti_callback, name='khalti_callback'),
    path('khalti-simulate/', views.khalti_simulate, name='khalti_simulate'),


    # Subscription management
    path('cancel-subscription/', views.cancel_subscription, name='cancel_subscription'),
]
