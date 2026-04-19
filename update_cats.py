import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lostandfound.settings')
django.setup()

from items.models import Category

updates = {
    "Electrical / Electronics": "💻 Electrical / Electronics",
    "Books & Stationery": "📚 Books & Stationery",
    "ID Cards & Documents": "💳 ID Cards & Documents",
    "Accessories": "⌚ Accessories",
    "Clothing": "👕 Clothing",
    "Keys": "🔑 Keys",
    "Others": "📦 Others"
}

for old_name, new_name in updates.items():
    try:
        cat = Category.objects.get(name=old_name)
        cat.name = new_name
        cat.save()
        print(f"Updated '{old_name}' -> '{new_name}'")
    except Category.DoesNotExist:
        # Check if it already has the emoji
        try:
            cat = Category.objects.get(name=new_name)
            print(f"Category already updated: '{new_name}'")
        except Category.DoesNotExist:
            print(f"Category '{old_name}' not found.")

print("Category update complete.")
