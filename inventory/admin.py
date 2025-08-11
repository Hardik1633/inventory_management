from django.contrib import admin
from .models import Product

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('product_code', 'product_name', 'unit_of_measure', 'current_stock')
    search_fields = ('product_code', 'product_name')
    list_filter = ('unit_of_measure',)
    ordering = ('product_code',)
    