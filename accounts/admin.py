from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Subscription, Transaction, KhaltiPayment

class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'user_type', 'is_premium', 'points_balance', 'premium_expiry']
    list_filter = ['user_type', 'is_premium', 'is_active']
    search_fields = ['username', 'email']

admin.site.register(User, CustomUserAdmin)

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'status', 'start_date', 'end_date', 'payment_amount']
    list_filter = ['status']

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'transaction_type', 'points', 'created_at']
    list_filter = ['transaction_type']

@admin.register(KhaltiPayment)
class KhaltiPaymentAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount', 'status', 'token', 'created_at']
    list_filter = ['status']
    search_fields = ['user__username', 'token']
