import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lostandfound.settings')
django.setup()

from items.models import Category

categories = [
    {"name": "Electrical / Electronics", "description": "Laptops, phones, chargers, earphones", "icon": "fa-laptop"},
    {"name": "Books & Stationery", "description": "Textbooks, notebooks, pens, calculators", "icon": "fa-book"},
    {"name": "ID Cards & Documents", "description": "Student IDs, licenses, wallets", "icon": "fa-id-card"},
    {"name": "Accessories", "description": "Watches, glasses, jewelry, bags", "icon": "fa-glasses"},
    {"name": "Clothing", "description": "Jackets, hoodies, caps", "icon": "fa-tshirt"},
    {"name": "Keys", "description": "Room keys, vehicle keys", "icon": "fa-key"},
    {"name": "Others", "description": "Anything else", "icon": "fa-box"}
]

for cat in categories:
    obj, created = Category.objects.get_or_create(
        name=cat["name"],
        defaults={"description": cat["description"], "icon": cat["icon"]}
    )
    if created:
        print(f"Created category: {cat['name']}")
    else:
        print(f"Category already exists: {cat['name']}")

print("Done generating categories.")
