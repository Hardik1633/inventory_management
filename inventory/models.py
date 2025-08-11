# inventory/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MinLengthValidator
from django.core.exceptions import ValidationError

# Get the User model
User = get_user_model()

class Product(models.Model):
    product_name = models.CharField(
        max_length=100,
        help_text="Display name of the product"
    )
    product_code = models.CharField(
        max_length=50,
        unique=True,
        validators=[MinLengthValidator(3)],
        help_text="Unique identifier for the product (min 3 chars)"
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed product information"
    )
    unit_of_measure = models.CharField(
        max_length=20,
        default='pcs',
        help_text="Measurement unit (e.g., pcs, kg, box)"
    )
    current_stock = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        editable=False,
        help_text="Automatically calculated stock level"
    )
    unit_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        help_text="Current unit price of the product"
    )
    
    class Meta:
        ordering = ['product_name']
        verbose_name = "Product"
        verbose_name_plural = "Products"
    
    def __str__(self):
        return f"{self.product_name} ({self.product_code})"
    
    @property
    def available_stock(self):
        """Read-only property showing available stock"""
        return self.current_stock
    
    def get_stock_movements(self):
        """Returns all transaction details affecting this product"""
        return TransactionDetail.objects.filter(product=self).select_related(
            'transaction'
        ).order_by('-transaction__transaction_date')
    
    def get_transactions(self):
        """Get all transactions involving this product"""
        return Transaction.objects.filter(products=self).select_related(
            'created_by'
        ).prefetch_related(
            'details'
        ).order_by('-transaction_date')

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('purchase', 'Purchase'),
        ('sale', 'Sale'),
        ('return', 'Return'),
        ('adjustment', 'Adjustment'),
    ]
    
    transaction_date = models.DateTimeField(auto_now_add=True)
    transaction_type = models.CharField(
        max_length=20, 
        choices=TRANSACTION_TYPES,
        help_text="Type of inventory transaction"
    )
    reference_number = models.CharField(
        max_length=50,
        blank=True,
        help_text="External reference number (invoice, PO, etc.)"
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional information about the transaction"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventory_transactions'
    )
    products = models.ManyToManyField(
        Product,
        through='TransactionDetail',
        related_name='transactions'
    )
    
    class Meta:
        ordering = ['-transaction_date']
        verbose_name = "Inventory Transaction"
        verbose_name_plural = "Inventory Transactions"
        db_table = 'inventory_transaction'
    
    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.reference_number or self.id}"
    
    def get_products_with_details(self):
        """Get products with their transaction quantities and prices"""
        return self.details.select_related('product').all()
    
    def clean(self):
        """Validate the transaction before saving"""
        super().clean()
        if self.transaction_type not in dict(self.TRANSACTION_TYPES).keys():
            raise ValidationError("Invalid transaction type")

class TransactionDetail(models.Model):
    transaction = models.ForeignKey(
        Transaction, 
        on_delete=models.CASCADE, 
        related_name='details'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='transaction_details'
    )
    quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        help_text="Quantity of product in this transaction"
    )
    unit_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Unit price at time of transaction (optional)"
    )
    
    class Meta:
        verbose_name = "Transaction Detail"
        verbose_name_plural = "Transaction Details"
        db_table = 'inventory_transactiondetail'
        constraints = [
            models.UniqueConstraint(
                fields=['transaction', 'product'],
                name='unique_transaction_product'
            )
        ]
    
    def __str__(self):
        return f"{self.product} - {self.quantity} @ {self.unit_price or 'N/A'}"
    
    def clean(self):
        """Validate transaction details before saving"""
        super().clean()
        
        # Skip validation if transaction is not yet saved
        if not self.transaction_id:
            return
            
        # Validate stock levels for outgoing transactions
        if self.transaction.transaction_type in ['sale']:
            if self.product.current_stock < self.quantity:
                raise ValidationError(
                    f"Insufficient stock for {self.product}. "
                    f"Available: {self.product.current_stock}, "
                    f"Requested: {self.quantity}"
                )
    
    def save(self, *args, **kwargs):
        """Automatically update product stock when saving transactions"""
        is_new = not self.pk
        
        if is_new:
            # Validate before saving
            self.clean()
            
            # Update product stock based on transaction type
            product = self.product
            if self.transaction.transaction_type in ['purchase', 'return', 'adjustment']:
                product.current_stock += self.quantity
            else:  # sale or other outgoing transactions
                product.current_stock -= self.quantity
            
            # Update unit price if provided
            if self.unit_price is not None:
                product.unit_price = self.unit_price
                
            product.save()
        
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Reverse stock adjustment when deleting a transaction detail"""
        product = self.product
        if self.transaction.transaction_type in ['purchase', 'return', 'adjustment']:
            product.current_stock -= self.quantity
        else:  # sale or other outgoing transactions
            product.current_stock += self.quantity
        product.save()
        super().delete(*args, **kwargs)