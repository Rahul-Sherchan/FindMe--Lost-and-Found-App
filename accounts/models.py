from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone


class User(AbstractUser):
    """Custom user model extending Django's AbstractUser"""
    USER_TYPE_CHOICES = (
        ('normal', 'Normal User'),
        ('premium', 'Premium User'),
        ('admin', 'Admin'),
    )
    
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='normal')
    phone_number = models.CharField(max_length=20, blank=True, null=True, help_text="Full phone number with country code")
    recovery_email = models.EmailField(blank=True, null=True, help_text="Optional recovery email for password resets")
    address = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    points_balance = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    is_premium = models.BooleanField(default=False)
    premium_expiry = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"
    
    @property
    def image_upload_limit(self):
        """Returns the image upload limit per post based on user type"""
        if self.is_premium or self.user_type == 'premium':
            return None  # Unlimited for premium users
        return 20  # 20 images per post for normal users

    def check_and_reset_premium(self):
        """Check if premium has expired and reset status"""
        if self.is_premium and self.premium_expiry and self.premium_expiry < timezone.now():
            self.is_premium = False
            self.user_type = 'normal'
            self.premium_expiry = None
            self.save(update_fields=['is_premium', 'user_type', 'premium_expiry'])
            
            # Mark active subscriptions as expired
            self.subscriptions.filter(status='active').update(status='expired')
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'


class Subscription(models.Model):
    """Track subscription history"""
    SUBSCRIPTION_STATUS = (
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()
    status = models.CharField(max_length=10, choices=SUBSCRIPTION_STATUS, default='active')
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Simulated payment
    payment_method = models.CharField(max_length=50, default='Simulated Payment')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.status} ({self.start_date.date()} to {self.end_date.date()})"
    
    class Meta:
        db_table = 'subscriptions'
        ordering = ['-created_at']


class Transaction(models.Model):
    """Track points transactions"""
    TRANSACTION_TYPE = (
        ('earned', 'Points Earned'),
        ('redeemed', 'Points Redeemed'),
        ('bonus', 'Bonus Points'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE)
    points = models.IntegerField(validators=[MinValueValidator(0)])
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.transaction_type} - {self.points} points"
    
    class Meta:
        db_table = 'transactions'
        ordering = ['-created_at']
