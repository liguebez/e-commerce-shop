from django.shortcuts import render, redirect
from django.urls import reverse
from .models import Order, OrderItem
from .forms import OrderCreateForm
from cart.models import CartItem
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.contrib import messages
from main.models import Product
from django.core.paginator import Paginator


@login_required
def order_create(request):
    cart = CartItem.objects.select_related('product').filter(user=request.user)
    if request.method == "POST":
        form = OrderCreateForm(request.POST, request=request)
        if form.is_valid():
            with transaction.atomic():
                for item in cart:
                    product = Product.objects.select_for_update().get(id=item.product_id)
                    if product.stock < item.quantity:
                        messages.error(
                            request,
                            f'Sorry, only {product.stock} unit(s) of '
                            f'"{product.name}" are available.'
                        )
                        return redirect('cart:cart_detail')
                
                order = form.save()
                for item in cart:
                    discounted_price = item.product.get_price()
                    OrderItem.objects.create(orders=order,
                                            product = item.product,
                                            price=discounted_price,
                                            quantity=item.quantity)

            request.session['order_id'] = order.id

            return redirect(reverse('payment:payment_process'))
    else:
        form = OrderCreateForm(request=request)
    
    return render(request, 'order/create.html', {'cart': cart, 'form': form})

@login_required
def order_list(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('items__product')
    paginator = Paginator(orders, 5)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'order/list.html', {'orders': page})

