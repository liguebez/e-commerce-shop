from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from main.models import Product
from orders.models import Order


class Command(BaseCommand):
    help = (
        'Restores reserved stock and deletes unpaid orders older than '
        'settings.ORDER_RESERVATION_MINUTES. Intended to run periodically '
        '(e.g. every few minutes via cron) to release stock held by carts '
        'that never completed a Stripe Checkout Session, since those never '
        'produce a checkout.session.expired webhook event.'
    )

    def handle(self, *args, **options):
        cutoff = timezone.now() - timezone.timedelta(
            minutes=settings.ORDER_RESERVATION_MINUTES
        )
        stale_orders = Order.objects.filter(paid=False, created__lt=cutoff)

        released = 0
        for order_id in stale_orders.values_list('id', flat=True):
            with transaction.atomic():
                try:
                    order = Order.objects.select_for_update().get(id=order_id)
                except Order.DoesNotExist:
                    continue

                if order.paid or order.created >= cutoff:
                    continue

                for item in order.items.all():
                    Product.objects.filter(id=item.product_id).update(
                        stock=F('stock') + item.quantity
                    )
                order.delete()
                released += 1

        self.stdout.write(self.style.SUCCESS(
            f'Released {released} expired order(s).'
        ))
