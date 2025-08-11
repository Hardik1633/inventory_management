# inventory/views.py
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy, reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import logout
from django.db.models import Sum, Case, When, Value, DecimalField, Q
from rest_framework import viewsets
from .models import Product, Transaction
from .forms import ProductForm, TransactionForm
from .serializers import ProductSerializer, TransactionSerializer


# API Views
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().order_by('product_code')
    serializer_class = ProductSerializer
    filterset_fields = ['product_code', 'product_name']
    search_fields = ['product_code', 'product_name', 'description']

class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all().order_by('-transaction_date')
    serializer_class = TransactionSerializer
    filterset_fields = ['transaction_type', 'created_by']
    search_fields = ['reference_number', 'notes']

# UI Views (protected with login required)
class TransactionCreateView(LoginRequiredMixin, CreateView):
    model = Transaction
    form_class = TransactionForm
    template_name = 'inventory/transaction_create.html'
    success_url = reverse_lazy('transaction_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, 'Transaction created successfully')
        return response

class TransactionListView(LoginRequiredMixin, ListView):
    model = Transaction
    template_name = 'inventory/transaction_list.html'
    context_object_name = 'transactions'
    ordering = ['-transaction_date']
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.select_related('created_by').prefetch_related('products', 'details')

def transaction_detail(request, transaction_id):
    if not request.user.is_authenticated:
        return redirect('login')
        
    transaction = get_object_or_404(
        Transaction.objects.select_related('created_by')
                          .prefetch_related('details__product'),
        id=transaction_id
    )
    return render(request, 'inventory/transaction_detail.html', {
        'transaction': transaction,
        'details': transaction.details.all()
    })

def inventory_transaction_change(request, pk):
    if not request.user.is_authenticated:
        return redirect('login')
        
    """
    View for changing/updating inventory transactions
    """
    transaction = get_object_or_404(
        Transaction.objects.select_related('created_by')
                          .prefetch_related('details__product'),
        pk=pk
    )
    
    if request.method == 'POST':
        form = TransactionForm(request.POST, instance=transaction)
        if form.is_valid():
            updated_transaction = form.save(commit=False)
            updated_transaction.modified_by = request.user
            updated_transaction.save()
            form.save_m2m()  # For many-to-many relationships
            
            # Update related product quantities if needed
            # (Add your specific business logic here)
            
            messages.success(request, 'Transaction updated successfully')
            return redirect('transaction_detail', transaction_id=pk)
    else:
        form = TransactionForm(instance=transaction)
    
    context = {
        'form': form,
        'transaction': transaction,
        'action': 'Update'
    }
    return render(request, 'inventory/transaction_create.html', context)

def transaction_delete(request, pk):
    if not request.user.is_authenticated:
        return redirect('login')
        
    """Delete an inventory transaction"""
    transaction = get_object_or_404(Transaction, pk=pk)
    
    if request.method == 'POST':
        if request.user.is_staff or transaction.created_by == request.user:
            transaction.delete()
            messages.success(request, 'Transaction deleted successfully')
            return redirect('transaction_list')
        else:
            messages.error(request, 'You do not have permission to delete this transaction')
    
    return redirect('transaction_list')

def inventory_report(request):
    if not request.user.is_authenticated:
        return redirect('login')
        
    products = Product.objects.annotate(
        total_in=Sum(
            Case(
                When(transaction_details__transaction__transaction_type__in=['purchase', 'return', 'adjustment'],
                     then='transaction_details__quantity'),
                default=Value(0),
                output_field=DecimalField()
            )
        ),
        total_out=Sum(
            Case(
                When(transaction_details__transaction__transaction_type__in=['sale'],
                     then='transaction_details__quantity'),
                default=Value(0),
                output_field=DecimalField()
            )
        )
    ).order_by('product_code')
    
    try:
        total_value = sum(
            float(p.current_stock) * float(p.unit_price or 0)
            for p in products
        )
    except (TypeError, ValueError):
        total_value = 0
    
    context = {
        'products': products,
        'total_value': total_value
    }
    return render(request, 'inventory/inventory_report.html', context)

class ProductListView(LoginRequiredMixin, ListView):
    model = Product
    template_name = 'inventory/product_list.html'
    context_object_name = 'products'
    paginate_by = 20
    ordering = ['product_code']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(product_code__icontains=search_query) |
                Q(product_name__icontains=search_query)
            )
        return queryset

class ProductCreateView(LoginRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'inventory/product_form.html'
    success_url = reverse_lazy('product_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Product {self.object.product_code} created successfully")
        return response

class ProductUpdateView(LoginRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'inventory/product_form.html'
    success_url = reverse_lazy('product_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Product {self.object.product_code} updated successfully")
        return response

class ProductDeleteView(LoginRequiredMixin, DeleteView):
    model = Product
    template_name = 'inventory/product_confirm_delete.html'
    success_url = reverse_lazy('product_list')
    
    def delete(self, request, *args, **kwargs):
        product = self.get_object()
        if product.current_stock != 0:
            messages.error(request, "Cannot delete product with existing stock")
            return self.get(request, *args, **kwargs)
        messages.success(request, f"Product {product.product_code} deleted")
        return super().delete(request, *args, **kwargs)

class ProductStockMovementsView(LoginRequiredMixin, DetailView):
    model = Product
    template_name = 'inventory/product_stock_movements.html'
    context_object_name = 'product'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.get_object()
        
        # Get all transaction details for this product
        details = product.transaction_details.select_related(
            'transaction', 'transaction__created_by'
        ).order_by('-transaction__transaction_date')
        
        # Calculate totals using aggregation
        totals = details.aggregate(
            total_in=Sum(
                Case(
                    When(transaction__transaction_type__in=['purchase', 'return', 'adjustment'],
                         then='quantity'),
                    default=Value(0),
                    output_field=DecimalField()
                )
            ),
            total_out=Sum(
                Case(
                    When(transaction__transaction_type='sale',
                         then='quantity'),
                    default=Value(0),
                    output_field=DecimalField()
                )
            )
        )
        
        context['movements'] = details
        context['total_in'] = totals['total_in'] or 0
        context['total_out'] = totals['total_out'] or 0
        
        return context

def direct_logout(request):
    logout(request)
    return redirect('login')