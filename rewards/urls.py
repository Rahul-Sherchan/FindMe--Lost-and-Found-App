from django.urls import path
from . import views

app_name = 'rewards'

urlpatterns = [
    path('', views.giftcard_catalog, name='giftcard_catalog'),
    path('<int:pk>/redeem/', views.redeem_giftcard, name='redeem_giftcard'),
    path('history/', views.redemption_history, name='redemption_history'),
]
