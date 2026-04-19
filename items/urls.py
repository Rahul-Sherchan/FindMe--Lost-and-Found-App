from django.urls import path
from . import views

app_name = 'items'

urlpatterns = [
    path('', views.item_list, name='item_list'),
    path('post/', views.post_item, name='post_item'),
    path('<int:pk>/', views.item_detail, name='item_detail'),
    path('my-items/', views.my_items, name='my_items'),
    path('my-claims/', views.my_claims, name='my_claims'),
    path('<int:pk>/edit/', views.edit_item, name='edit_item'),
    path('<int:pk>/delete/', views.delete_item, name='delete_item'),
    path('<int:pk>/claim/', views.submit_claim, name='submit_claim'),
    path('claim/<int:claim_id>/review/', views.review_claim, name='review_claim'),
    path('<int:pk>/resolve/', views.mark_as_resolved, name='mark_resolved'),
    path('<int:pk>/verify-reward/', views.verify_reward_payment, name='verify_reward'),
]
