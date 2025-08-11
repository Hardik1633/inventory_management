# inventory/urls_ui.py
from django.urls import path
from . import views

urlpatterns = [
    path('inventory/', views.inventory_report, name='inventory_report'),
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('transactions/', views.TransactionListView.as_view(), name='transaction_list'),
    path('transactions/new/', views.TransactionCreateView.as_view(), name='transaction_create'),
    path('', views.inventory_report, name='home'),  # Root URL
]