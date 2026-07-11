import logging
import stripe
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail
from django.template.loader import render_to_string
from orders.models import Order
from main.models import Product
from django.db.models import F
from orders.models import OrderItem
from cart.models import CartItem
from django.db import transaction

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    if not sig_header:
        return HttpResponse(status=400)
    event = None
    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        return HttpResponse(status=400)

    if event.type == 'checkout.session.completed':
        session = event.data.object
        if session.mode == 'payment' and session.payment_status == 'paid':
            with transaction.atomic():
                try:
                    order = Order.objects.select_for_update().get(id=session.client_reference_id)
                except Order.DoesNotExist:
                    return HttpResponse(status=400)
                
                if order.paid:
                    return HttpResponse(status=200)

                order.paid = True
                order.status = 'processing'
                order.stripe_id = session.payment_intent
                order.save()

                CartItem.objects.filter(
                    user=order.user,
                    product_id__in=order.items.values_list('product_id', flat=True)
                ).delete()

            try:
                subject = f'Order #{order.id} confirmed'
                body = render_to_string('order/email_confirmation.txt', {'order': order})
                send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [order.email])
            except Exception:
                logging.getLogger(__name__).error(
                    f'Failed to send confirmation email for order {order.id}', exc_info=True
                )


    elif event.type == 'checkout.session.expired':
        session = event.data.object
        with transaction.atomic():
            try:
                order = Order.objects.select_for_update().get(id=session.client_reference_id)
            except Order.DoesNotExist:
                return HttpResponse(status=200)

            if not order.paid:
                for item in order.items.all():
                    Product.objects.filter(id=item.product_id).update(
                        stock=F('stock') + item.quantity
                    )
                order.delete()

    return HttpResponse(status=200)