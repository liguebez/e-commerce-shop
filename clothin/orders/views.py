from django.shortcuts import render, redirect
from django.urls import reverse
from .models import Order, OrderItem
from .forms import OrderCreateForm
from cart.models import CartItem

def order_create(request):
    cart = CartItem.objects.select_related('product').filter(user=request.user)
    if request.method == "POST":
        form = OrderCreateForm(request.POST, request=request)
        if form.is_valid():
            order = form.save()
            for item in cart:
                discounted_price = item.product.get_price()
                OrderItem.objects.create(orders=order,
                                         product = item.product,
                                         price=discounted_price,
                                         quantity=item.quantity)
            cart.delete()
            request.session['order_id'] = order.id
            return redirect(reverse('payment:payment_process'))
    else:
        form = OrderCreateForm(request=request)
        return render(request, 'order/create.html', {'cart': cart, 'form': form})