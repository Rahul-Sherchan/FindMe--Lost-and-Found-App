from django.urls import path
from . import views

app_name = 'messaging'

urlpatterns = [
    path('', views.conversation_list, name='conversation_list'),
    path('<int:pk>/', views.conversation_detail, name='conversation_detail'),
    path('start/<int:item_pk>/', views.start_conversation, name='start_conversation'),
    path('start-admin/<int:user_pk>/', views.start_admin_conversation, name='start_admin_conversation'),
]
