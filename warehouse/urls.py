# from django.contrib import admin
# from django.urls import path, include
# from django.views.generic import RedirectView

# urlpatterns = [
#     path('admin/', admin.site.urls),
#     path('inventory/', include('inventory.urls')),
#     path('', RedirectView.as_view(url='inventory/')),  # Redirect root to inventory
# ]
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LoginView
from inventory import views  # Import views from inventory

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/', LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', views.direct_logout, name='logout'),  # Use direct logout view
    path('', include('inventory.urls')),
]