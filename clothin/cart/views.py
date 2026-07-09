from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from urllib.parse import urlparse
from main.models import Product
from .forms import CartAddProductForm, CartUpdateForm
from .models import CartItem

from decimal import Decimal


def _login_redirect(request):
    referer = request.META.get('HTTP_REFERER', '/')
    referer_path = urlparse(referer).path or '/'
    return redirect(f"{reverse('users:login')}?next={referer_path}")


def _safe_referer_redirect(request):
    referer = request.META.get('HTTP_REFERER', '/')
    if url_has_allowed_host_and_scheme(referer, allowed_hosts={request.get_host()}):
        return redirect(referer)
    return redirect('/')


@require_POST
def cart_add(request, product_id):
    if not request.user.is_authenticated:
        return _login_redirect(request)
    product = get_object_or_404(Product, id=product_id, available=True)
    item, created = CartItem.objects.get_or_create(user=request.user, product=product)

    if not created:
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
                if item.quantity > product.stock:
                    messages.error(request, f'Only {product.stock} units available.')
                    return redirect('cart:cart_detail')
                item.save()

    return _safe_referer_redirect(request)

@require_POST
def cart_update(request, product_id):
    if not request.user.is_authenticated:
        return _login_redirect(request)
    product = get_object_or_404(Product, id=product_id, available=True)
    item, _ = CartItem.objects.get_or_create(user=request.user, product=product)
    form = CartUpdateForm(request.POST)

    if form.is_valid():
        cd = form.cleaned_data
        item.quantity = cd['quantity']
        if item.quantity > product.stock:
            messages.error(request, f'Only {product.stock} units available.')
            return redirect('cart:cart_detail')
        item.save()

    return redirect('cart:cart_detail')

@require_POST
def cart_remove(request, product_id):
    if not request.user.is_authenticated:
        return _login_redirect(request)
    product = get_object_or_404(Product, id=product_id, available=True)
    CartItem.objects.filter(user=request.user, product=product).delete()

    return _safe_referer_redirect(request)


@login_required
def cart_detail(request):
    items = CartItem.objects.filter(user=request.user).select_related('product')

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
