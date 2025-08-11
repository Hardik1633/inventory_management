from django import forms
from django.core.exceptions import ValidationError
from .models import Product, Transaction, TransactionDetail

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'product_code', 
            'product_name',
            'description',
            'unit_of_measure',
            'unit_price'
        ]
        widgets = {
            'description': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'Enter product description'
            }),
            'product_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. PROD-001'
            }),
            'product_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter product name'
            }),
            'unit_of_measure': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. pcs, kg, box'
            }),
            'unit_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            })
        }
        help_texts = {
            'product_code': 'Unique identifier for the product (3-50 characters)',
            'unit_price': 'Price per unit in the base currency'
        }
    
    def clean_product_code(self):
        code = self.cleaned_data['product_code'].upper().strip()
        if not code:
            raise ValidationError("Product code cannot be empty")
        return code

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['transaction_type', 'reference_number', 'notes']
        widgets = {
            'transaction_type': forms.Select(attrs={
                'class': 'form-select',
            }),
            'reference_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Optional reference number'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Additional notes about this transaction'
            })
        }
        labels = {
            'reference_number': 'Reference #'
        }

class TransactionDetailForm(forms.ModelForm):
    class Meta:
        model = TransactionDetail
        fields = ['product', 'quantity', 'unit_price']
        widgets = {
            'product': forms.Select(attrs={
                'class': 'form-select product-select',
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01'
            }),
            'unit_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            })
        }
        help_texts = {
            'unit_price': 'Leave blank to use product default price'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.product:
            self.fields['unit_price'].initial = self.instance.product.unit_price

    def clean_quantity(self):
        quantity = self.cleaned_data['quantity']
        if quantity <= 0:
            raise ValidationError("Quantity must be greater than zero")
        return quantity

    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        quantity = cleaned_data.get('quantity')
        
        if product and quantity:
            if self.instance.transaction.transaction_type in ['sale']:
                if product.current_stock < quantity:
                    raise ValidationError(
                        f"Insufficient stock. Available: {product.current_stock}"
                    )
        return cleaned_data