from django.urls import path
from . import views

app_name = 'rewards'

urlpatterns = [
    # Main rewards dashboard — shows points, history, redeem button
    path('', views.rewards_dashboard, name='rewards_dashboard'),

    # Submit a redeem request (premium users only)
    path('redeem/', views.submit_redeem, name='submit_redeem'),

    # My redeem request history
    path('my-requests/', views.my_redeem_requests, name='my_redeem_requests'),
]
