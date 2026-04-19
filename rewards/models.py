from django.db import models
from django.core.validators import MinValueValidator
from accounts.models import User


# ─────────────────────────────────────────────
#  Redemption Request
#  A premium user requests to convert their
#  reward points into real money (Rs.).
#  Admin reviews, approves, then marks as paid.
# ─────────────────────────────────────────────

class RedeemRequest(models.Model):
    """
    Stores a user's request to redeem reward points for money.

    Business Rules (easy to explain in viva):
    - Only premium users can submit (enforced in views)
    - Minimum 500 points required
    - Conversion rate: 100 points = Rs. 50
    - Points are deducted ONLY when admin approves the request
    - Admin manually pays the user, then clicks "Mark as Paid"

    Status flow:
      Pending → Approved → Paid
      Pending → Rejected
    """

    STATUS_CHOICES = (
        ('pending',  'Pending'),    # waiting for admin review
        ('approved', 'Approved'),   # admin approved, points deducted
        ('rejected', 'Rejected'),   # admin rejected, no points deducted
        ('paid',     'Paid'),       # admin confirmed manual payment sent
    )

    # The user who submitted this request
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='redeem_requests'
    )

    # How many points the user wants to redeem
    points_requested = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Number of points to redeem (minimum 500)"
    )

    # Equivalent NPR amount — calculated automatically
    # Formula: (points_requested / 100) * 50
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Equivalent amount in NPR"
    )

    # Current status of this request
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending'
    )

    # User's Khalti number or preferred payment contact
    # This helps admin know where to send the payout
    payout_reference = models.CharField(
        max_length=200,
        blank=True,
        default='',
        help_text="User's Khalti number or preferred payment method info"
    )

    # When the user submitted the request
    requested_at = models.DateTimeField(auto_now_add=True)

    # When admin approved or rejected the request
    reviewed_at = models.DateTimeField(null=True, blank=True)

    # When admin confirmed payment was sent (status = paid)
    paid_at = models.DateTimeField(null=True, blank=True)

    # Optional note from admin (rejection reason, payment reference, etc.)
    admin_note = models.TextField(blank=True, default='')

    def __str__(self):
        return f"{self.user.username} — {self.points_requested} pts — {self.get_status_display()}"

    class Meta:
        db_table = 'redeem_requests'
        ordering = ['-requested_at']
