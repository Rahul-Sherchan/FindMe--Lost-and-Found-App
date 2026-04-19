from django import forms
from .models import RedeemRequest

# Business rules (same as views.py — easy to update for viva)
MIN_REDEEM_PTS = 500


class RedeemRequestForm(forms.Form):
    """
    Simple form for submitting a redeem request.
    The user chooses how many points to redeem and provides
    their Khalti number so admin knows where to send the payment.
    """

    points_requested = forms.IntegerField(
        min_value=MIN_REDEEM_PTS,
        label="Points to Redeem",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'id': 'points_requested',
            'placeholder': f'Minimum {MIN_REDEEM_PTS} points',
        }),
        help_text=f"Minimum {MIN_REDEEM_PTS} points required."
    )

    payout_reference = forms.CharField(
        max_length=200,
        required=False,
        label="Khalti Number / Payment Info",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'id': 'payout_reference',
            'placeholder': 'e.g. 98XXXXXXXX (your Khalti/eSewa number)',
        }),
        help_text="Optional: Enter your Khalti number so admin can send payment."
    )
