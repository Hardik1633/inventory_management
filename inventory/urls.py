from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import (
    ProductListView,
    ProductCreateView,
    ProductUpdateView,
    ProductDeleteView,
    TransactionCreateView,
    TransactionListView,
    inventory_report,
    ProductStockMovementsView
)

# Initialize DefaultRouter for API endpoints
router = DefaultRouter()
router.register(r'products', views.ProductViewSet, basename='product')
router.register(r'transactions', views.TransactionViewSet, basename='transaction')

urlpatterns = [
    
    # Product CRUD URLs
    path('products/', ProductListView.as_view(), name='product_list'),
    path('products/new/', ProductCreateView.as_view(), name='product_create'),
    path('products/<int:pk>/edit/', ProductUpdateView.as_view(), name='product_update'),
    path('products/<int:pk>/delete/', ProductDeleteView.as_view(), name='product_delete'),
    path('products/<int:pk>/movements/', 
         ProductStockMovementsView.as_view(), 
         name='product_stock_movements'),
    
    # Transaction URLs
    path('transactions/', TransactionListView.as_view(), name='transaction_list'),
    path('transactions/new/', TransactionCreateView.as_view(), name='transaction_create'),
    path('transactions/<int:pk>/change/', views.inventory_transaction_change, name='transaction_change'),
    path('transactions/<int:pk>/delete/', views.transaction_delete, name='transaction_delete'),  # Add this line
    path('transaction/<int:transaction_id>/', 
         views.transaction_detail, 
         name='transaction_detail'),
    
    # Inventory Report
    path('inventory/', inventory_report, name='inventory_report'),
    path('', views.inventory_report, name='inventory_report'),
    
    # API URLs
    path('api/', include(router.urls)),
]