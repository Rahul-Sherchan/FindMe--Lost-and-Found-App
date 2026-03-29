from django.db import models
from django.core.validators import MinValueValidator
from accounts.models import User


class GiftCard(models.Model):
    """Available gift cards for redemption"""
    name = models.CharField(max_length=200)
    description = models.TextField()
    brand = models.CharField(max_length=100)
    points_required = models.IntegerField(validators=[MinValueValidator(1)])
    value = models.DecimalField(max_digits=10, decimal_places=2, help_text="Gift card value (for display)")
    image = models.ImageField(upload_to='giftcards/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    stock = models.IntegerField(default=0, help_text="Available quantity (0 = unlimited)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} - {self.points_required} points"
    
    @property
    def is_available(self):
        """Check if gift card is available for redemption"""
        if not self.is_active:
            return False
        if self.stock == 0:  # Unlimited
            return True
        return self.stock > 0
    
    class Meta:
        db_table = 'giftcards'
        ordering = ['points_required']


class Redemption(models.Model):
    """User redemption history"""
    REDEMPTION_STATUS = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='redemptions')
    giftcard = models.ForeignKey(GiftCard, on_delete=models.SET_NULL, null=True, related_name='redemptions')
    points_spent = models.IntegerField(validators=[MinValueValidator(1)])
    status = models.CharField(max_length=10, choices=REDEMPTION_STATUS, default='pending')
    code = models.CharField(max_length=100, blank=True, help_text="Gift card code (simulated)")
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.giftcard.name if self.giftcard else 'Deleted Gift Card'}"
    
    class Meta:
        db_table = 'redemptions'
        ordering = ['-created_at']
