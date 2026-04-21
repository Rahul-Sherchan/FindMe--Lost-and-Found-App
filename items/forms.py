from django import forms
from .models import Item, ItemImage, Claim, Category
from django.core.exceptions import ValidationError


class ItemForm(forms.ModelForm):
    """Form for posting lost/found items"""
    class Meta:
        model = Item
        fields = ['item_type', 'category', 'title', 'description', 'location', 
                  'landmark', 'date_lost_found', 'reward_points']
        widgets = {
            'item_type': forms.Select(attrs={'id': 'post-type-select'}),
            'description': forms.Textarea(attrs={'rows': 4}),
            'date_lost_found': forms.DateInput(attrs={'type': 'date'}),
        }
        labels = {
            'item_type': 'Post Type',
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Make reward_points optional for found items
        self.fields['reward_points'].required = False
        self.fields['landmark'].required = False

    def clean(self):
        cleaned_data = super().clean()
        item_type = cleaned_data.get('item_type')
        reward_points = cleaned_data.get('reward_points')

        if item_type == 'found' and reward_points:
            # Reject reward points for found items (force to 0 or raise error)
            # We raise a validation error here to meet strict backend rejection requirement
            self.add_error('reward_points', 'Reward points cannot be set for found items.')
            cleaned_data['reward_points'] = 0
            
        return cleaned_data


class ItemImageForm(forms.ModelForm):
    """Form for uploading item images"""
    class Meta:
        model = ItemImage
        fields = ['image', 'caption', 'is_primary']
        widgets = {
            'caption': forms.TextInput(attrs={'placeholder': 'Optional caption'}),
        }
    
    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            # Validate file extension
            ext = image.name.split('.')[-1].lower()
            if ext not in ['jpg', 'jpeg', 'png']:
                raise ValidationError('Only .jpg, .jpeg, and .png files are allowed.')
            
            # Validate file size (max 5MB)
            if image.size > 5 * 1024 * 1024:
                raise ValidationError('Image file size must be less than 5MB.')
        
        return image


class ItemSearchForm(forms.Form):
    """Form for searching and filtering items"""
    query = forms.CharField(
        max_length=200, 
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Search by keyword...'})
    )
    item_type = forms.ChoiceField(
        choices=[('', 'All Types'), ('lost', 'Lost Items'), ('found', 'Found Items')],
        required=False
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label='All Categories'
    )
    location = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Location'})
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'placeholder': 'From date'})
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'placeholder': 'To date'})
    )


class ClaimForm(forms.ModelForm):
    """Form for submitting a claim"""
    class Meta:
        model = Claim
        fields = ['full_name', 'contact_number', 'message', 'proof_details', 'proof_image']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'placeholder': 'Your Full Name'
            }),
            'contact_number': forms.TextInput(attrs={
                'placeholder': 'Your Contact Number'
            }),
            'message': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Explain why you are claiming this item (e.g., this is my lost wallet)...'
            }),
            'proof_details': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Provide details that prove ownership (e.g. what is inside the wallet, serial numbers, password, etc.)...'
            }),
        }
