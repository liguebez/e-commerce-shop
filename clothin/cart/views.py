from django.shortcuts import render
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from main.models import Product
from .forms import CartAddProductForm, CartUpdateForm
from .models import CartItem

from decimal import Decimal

@login_required
@require_POST
def cart_add(request, product_id):
    product = get_object_or_404(Product, id=product_id, available=True)
    item, _ = CartItem.objects.get_or_create(user=request.user, product=product)
    form = CartAddProductForm(request.POST)

    if form.is_valid():
        cd = form.cleaned_data
        action = cd['action']
        if action == 'increment':
            item.quantity += 1  
        elif action == 'decrement':
            item.quantity -= 1
        
        if item.quantity <= 0:
            item.delete()
        else:
            item.save()

    return redirect(request.META.get('HTTP_REFERER', '/'))

@require_POST
@login_required
def cart_update(request, product_id):
    product = get_object_or_404(Product, id=product_id, available=True)
    item, _ = CartItem.objects.get_or_create(user=request.user, product=product)
    form = CartUpdateForm(request.POST)

    if form.is_valid():
        cd = form.cleaned_data
        item.quantity += cd['quantity']
        item.save()

    return redirect('cart:cart_detail')

@require_POST
def cart_remove(request, product_id):
    product = get_object_or_404(Product, id=product_id, available=True)
    CartItem.objects.filter(user=request.user, product=product).delete()

    return redirect(request.META.get('HTTP_REFERER', '/'))


@login_required
def cart_detail(request):
    
    items = CartItem.objects.filter(user=request.user).select_related('user')

    cart = []
    total = Decimal('0')
    for item in items:
        unit_price = Decimal(item.product.get_price())
        total += unit_price * item.quantity

        cart.append({
            'product': item.product,
            'quantity': item.quantity,
        })

    return render(request, 'cart/detail.html', {'cart' : cart, 'total': total})