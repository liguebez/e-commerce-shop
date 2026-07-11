from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from decimal import Decimal
from orders.models import Order, OrderItem
from cart.models import CartItem
from django.conf import settings
from django.contrib.auth.decorators import login_required
import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY
stripe.api_version = settings.STRIPE_API_VERSION

@login_required
def payment_process(request):
    order_id = request.session.get('order_id', None)
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if request.method == "POST":
        success_url = request.build_absolute_uri(
            reverse('payment:payment_completed')
        )
        cancel_url = request.build_absolute_uri(
            reverse('payment:payment_cancelled')
        )
        session_data = {
            'mode': 'payment',
            'client_reference_id': order.id,
            'success_url': success_url,
            'cancel_url': cancel_url,
            'line_items': [],
        }
        for item in order.items.all():
            session_data['line_items'].append({
                'price_data': {
                    'unit_amount': int(item.price * Decimal('100')),
                    'currency' : 'usd',
                    'product_data': {
                        'name': item.product.name,
                    }
                },
                'quantity': item.quantity,
            })
        session = stripe.checkout.Session.create(**session_data)
        return redirect(session.url, code=303)
    else:
        return render(request, 'payment/process.html', {'order': order})

def payment_completed(request):
    request.session.pop('order_id', None)
    return render(request, 'payment/completed.html')


def payment_cancelled(request):
    request.session.pop('order_id', None)
    return render(request, 'payment/cancelled.html')