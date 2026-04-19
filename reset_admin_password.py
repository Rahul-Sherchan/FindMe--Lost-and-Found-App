import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lostandfound.settings')
django.setup()

from accounts.models import User

# Reset Rahul's password to admin123
user = User.objects.get(username='Rahul')
user.set_password('admin123')
user.save()
print(f"✓ Password reset for {user.username}")
print(f"  Username: Rahul")
print(f"  Password: admin123")
