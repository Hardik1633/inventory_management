from rest_framework import serializers
from .models import Product, Transaction, TransactionDetail

class ProductSerializer(serializers.ModelSerializer):
    available_stock = serializers.DecimalField(
        source='current_stock',
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    
    class Meta:
        model = Product
        fields = [
            'id',
            'product_code',
            'product_name',
            'description',
            'unit_of_measure',
            'unit_price',
            'available_stock',
            'created_at',
            'updated_at'
        ]
        extra_kwargs = {
            'product_code': {
                'min_length': 3,
                'help_text': 'Unique identifier for the product (3-50 characters)'
            },
            'current_stock': {'read_only': True},
            'created_at': {'read_only': True},
            'updated_at': {'read_only': True}
        }

class TransactionDetailSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source='product',
        write_only=True,
        help_text='ID of the product involved in this transaction'
    )
    total_value = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
        help_text='Calculated value of this line item (quantity × unit_price)'
    )
    
    class Meta:
        model = TransactionDetail
        fields = [
            'id',
            'product',
            'product_id',
            'quantity',
            'unit_price',
            'total_value',
            'created_at'
        ]
        extra_kwargs = {
            'quantity': {
                'min_value': 0.01,
                'help_text': 'Quantity of product in this transaction'
            },
            'unit_price': {
                'min_value': 0,
                'required': False,
                'help_text': 'Price per unit at time of transaction (optional)'
            },
            'created_at': {'read_only': True}
        }

    def validate(self, attrs):
        if self.context['request'].method in ['POST', 'PUT', 'PATCH']:
            transaction_type = self.context.get('transaction_type')
            product = attrs.get('product')
            quantity = attrs.get('quantity')
            
            if transaction_type in ['sale'] and product.current_stock < quantity:
                raise serializers.ValidationError(
                    f"Insufficient stock for {product.product_code}. "
                    f"Available: {product.current_stock}, Requested: {quantity}"
                )
        return attrs

class TransactionSerializer(serializers.ModelSerializer):
    details = TransactionDetailSerializer(many=True, required=False)
    created_by = serializers.StringRelatedField(read_only=True)
    total_value = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
        help_text='Total value of all items in this transaction'
    )
    
    class Meta:
        model = Transaction
        fields = [
            'id',
            'transaction_type',
            'transaction_date',
            'reference_number',
            'notes',
            'created_by',
            'details',
            'total_value',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'created_by',
            'transaction_date',
            'total_value',
            'created_at',
            'updated_at'
        ]
        extra_kwargs = {
            'reference_number': {
                'required': False,
                'allow_blank': True,
                'help_text': 'Optional reference number (PO, invoice, etc.)'
            },
            'notes': {
                'required': False,
                'allow_blank': True,
                'help_text': 'Additional notes about this transaction'
            }
        }

    def validate(self, data):
        transaction_type = data.get('transaction_type')
        details = data.get('details', [])
        
        if transaction_type in ['sale'] and not details:
            raise serializers.ValidationError(
                "Transaction details are required for sales"
            )
        
        return data

    def create(self, validated_data):
        details_data = validated_data.pop('details', [])
        request = self.context.get('request')
        
        transaction = Transaction.objects.create(
            **validated_data,
            created_by=request.user if request else None
        )
        
        for detail_data in details_data:
            TransactionDetail.objects.create(
                transaction=transaction,
                product=detail_data['product'],
                quantity=detail_data['quantity'],
                unit_price=detail_data.get('unit_price')
            )
        
        return transaction

    def update(self, instance, validated_data):
        details_data = validated_data.pop('details', None)
        
        # Update transaction fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Handle details update if provided
        if details_data is not None:
            current_details = instance.details.all()
            current_details.delete()
            
            for detail_data in details_data:
                TransactionDetail.objects.create(
                    transaction=instance,
                    product=detail_data['product'],
                    quantity=detail_data['quantity'],
                    unit_price=detail_data.get('unit_price')
                )
        
        return instance