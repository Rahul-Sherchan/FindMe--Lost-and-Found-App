from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import User
from items.models import Category
from rewards.models import GiftCard


class Command(BaseCommand):
    help = 'Populate database with initial data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Populating database...')
        
        # Create categories
        categories = [
            {'name': 'Electronics', 'description': 'Phones, laptops, tablets, etc.', 'icon': 'fa-mobile'},
            {'name': 'Documents', 'description': 'ID cards, passports, certificates, etc.', 'icon': 'fa-id-card'},
            {'name': 'Personal Items', 'description': 'Wallets, bags, keys, etc.', 'icon': 'fa-wallet'},
            {'name': 'Pets', 'description': 'Lost or found pets', 'icon': 'fa-paw'},
            {'name': 'Jewelry', 'description': 'Rings, necklaces, watches, etc.', 'icon': 'fa-gem'},
            {'name': 'Others', 'description': 'Other items', 'icon': 'fa-box'},
        ]
        
        for cat_data in categories:
            category, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'description': cat_data['description'],
                    'icon': cat_data['icon']
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created category: {category.name}'))
        
        # Create admin user
        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_superuser(
                username='admin',
                email='admin@lostandfound.com',
                password='admin123',
                user_type='admin',
                is_premium=True
            )
            self.stdout.write(self.style.SUCCESS('Created admin user (username: admin, password: admin123)'))
        
        # Create sample users
        sample_users = [
            {'username': 'john_doe', 'email': 'john@example.com', 'user_type': 'normal'},
            {'username': 'jane_smith', 'email': 'jane@example.com', 'user_type': 'premium', 'is_premium': True},
        ]
        
        for user_data in sample_users:
            if not User.objects.filter(username=user_data['username']).exists():
                user = User.objects.create_user(
                    username=user_data['username'],
                    email=user_data['email'],
                    password='password123',
                    user_type=user_data['user_type'],
                    is_premium=user_data.get('is_premium', False),
                    points_balance=100
                )
                self.stdout.write(self.style.SUCCESS(f'Created user: {user.username}'))
        
        # Create gift cards
        giftcards = [
            {'name': 'Daraz NPR 500 Gift Card', 'brand': 'Daraz', 'points_required': 500, 'value': 500},
            {'name': 'Foodmandu NPR 300 Voucher', 'brand': 'Foodmandu', 'points_required': 300, 'value': 300},
            {'name': 'Pathao NPR 200 Credit', 'brand': 'Pathao', 'points_required': 200, 'value': 200},
            {'name': 'Steam NPR 1000 Gift Card', 'brand': 'Steam', 'points_required': 1000, 'value': 1000},
            {'name': 'Netflix 1 Month Subscription', 'brand': 'Netflix', 'points_required': 800, 'value': 800},
        ]
        
        for gc_data in giftcards:
            giftcard, created = GiftCard.objects.get_or_create(
                name=gc_data['name'],
                defaults={
                    'brand': gc_data['brand'],
                    'points_required': gc_data['points_required'],
                    'value': gc_data['value'],
                    'description': f'{gc_data["brand"]} gift card worth NPR {gc_data["value"]}',
                    'is_active': True,
                    'stock': 0  # Unlimited
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created gift card: {giftcard.name}'))
        
        self.stdout.write(self.style.SUCCESS('Database populated successfully!'))
