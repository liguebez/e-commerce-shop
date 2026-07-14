from django.shortcuts import render, redirect
from django.urls import reverse
from .models import Order, OrderItem
from .forms import OrderCreateForm
from cart.models import CartItem
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F
from django.contrib import messages
from main.models import Product
from django.core.paginator import Paginator
from django.core.cache import cache


@login_required
def order_create(request):
    cart = CartItem.objects.select_related('product').filter(user=request.user).order_by('product_id')
    if request.method == "POST":
        form = OrderCreateForm(request.POST, request=request)
        if form.is_valid():
            if not cart.exists():
                messages.error(request, 'Your cart is empty.')
                return redirect('cart:cart_detail')
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

                # Reserve stock for every item only after confirming the whole
                # cart is available, so a shortfall further down the cart
                # can't leave earlier items decremented with no order to
                # release them later.
                for item in cart:
                    Product.objects.filter(id=item.product_id).update(
                        stock=F('stock') - item.quantity
                    )

                order = form.save()
                for item in cart:
                    discounted_price = item.product.get_price()
                    OrderItem.objects.create(orders=order,
                                            product = item.product,
                                            price=discounted_price,
                                            quantity=item.quantity)
                cart.delete()
                cache.delete(f'cart:v1:totals:user:{request.user.id}')

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

