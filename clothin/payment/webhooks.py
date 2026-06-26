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

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
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
            try:
                order = Order.objects.get(id=session.client_reference_id)
            except Order.DoesNotExist:
                return HttpResponse(400)
            order.paid = True
            order.status = 'processing'
            order.stripe_id = session.payment_intent
            order.save()

            for item in order.items.select_related('product'):
                updated = (
                    Product.objects.filter(id=item.product_id,
                                           stock__gte=item.quantity).update(stock=F('stock') - item.quantity
                                            )
                )

                # if updated:
                #     product = Product.objects.get(id=item.product_id)
                #     if product.stock <= 0:
                #         product.available = False
                #         product.save(update_fields=['available'])

            subject = f'Order #{order.id} confirmed'
            body = render_to_string('order/email_confirmation.txt', {'order': order})
            send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [order.email])

    elif event.type == 'checkout.session.expired':
        session = event.data.object
        try:
            order = Order.objects.get(id=session.client_reference_id)
        except Order.DoesNotExist:
            return HttpResponse(status=200)

        if not order.paid:
            order.delete()

    return HttpResponse(status=200)