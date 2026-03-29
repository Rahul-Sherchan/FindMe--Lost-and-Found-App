from django.db import models
from django.core.validators import MinValueValidator, FileExtensionValidator
from accounts.models import User


class Category(models.Model):
    """Item categories"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Icon class name (e.g., 'fa-mobile')")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        db_table = 'categories'
        verbose_name_plural = 'Categories'
        ordering = ['name']


class Item(models.Model):
    """Base model for lost and found items"""
    ITEM_TYPE_CHOICES = (
        ('lost', 'Lost Item'),
        ('found', 'Found Item'),
    )
    
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('claimed', 'Claimed'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='items')
    item_type = models.CharField(max_length=10, choices=ITEM_TYPE_CHOICES)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='items')
    title = models.CharField(max_length=200)
    description = models.TextField()
    location = models.CharField(max_length=255, help_text="Location where item was lost/found")
    landmark = models.CharField(max_length=255, blank=True, help_text="Nearby landmark")
    date_lost_found = models.DateField(help_text="Date when item was lost or found")
    reward_points = models.IntegerField(default=0, validators=[MinValueValidator(0)], 
                                       help_text="Points offered as reward (for lost items)")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    views_count = models.IntegerField(default=0)
    is_approved = models.BooleanField(default=True)  # Admin can moderate
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.get_item_type_display()}: {self.title}"
    
    class Meta:
        db_table = 'items'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['item_type', 'status']),
            models.Index(fields=['category', 'location']),
        ]


class ItemImage(models.Model):
    """Multiple images for each item"""
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(
        upload_to='item_images/',
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])]
    )
    caption = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Image for {self.item.title}"
    
    class Meta:
        db_table = 'item_images'
        ordering = ['-is_primary', 'uploaded_at']


class Claim(models.Model):
    """Claims submitted when someone finds a lost item"""
    CLAIM_STATUS = (
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='claims')
    claimant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='claims_made')
    message = models.TextField(help_text="Message to the owner explaining how you found the item")
    proof_image = models.ImageField(
        upload_to='claim_proofs/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])]
    )
    status = models.CharField(max_length=10, choices=CLAIM_STATUS, default='pending')
    admin_notes = models.TextField(blank=True, help_text="Admin notes for approval/rejection")
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                   related_name='claims_reviewed')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Claim by {self.claimant.username} for {self.item.title}"
    
    class Meta:
        db_table = 'claims'
        ordering = ['-created_at']
