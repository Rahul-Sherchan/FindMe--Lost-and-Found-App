"""
URL configuration for lostandfound project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render
from items.models import Item


def home(request):
    """Homepage view"""
    recent_lost = Item.objects.filter(item_type='lost', is_approved=True, status='active').order_by('-created_at')[:6]
    recent_found = Item.objects.filter(item_type='found', is_approved=True, status='active').order_by('-created_at')[:6]
    
    context = {
        'recent_lost': recent_lost,
        'recent_found': recent_found,
    }
    return render(request, 'home.html', context)


urlpatterns = [
    path("admin/", admin.site.urls),
    path('', home, name='home'),
    path('accounts/', include('accounts.urls')),
    path('items/', include('items.urls')),
    path('messaging/', include('messaging.urls')),
    path('notifications/', include('notifications.urls')),
    path('rewards/', include('rewards.urls')),
    path('admin-panel/', include('admin_dashboard.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
