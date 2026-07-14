from .models import CartItem
from decimal import Decimal
from django.core.cache import cache


def cart(request):
    if request.user.is_authenticated:

        cache_key = f'cart:v1:totals:user:{request.user.id}'
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        total_units = 0
        after_price = Decimal('0')
        before_price = Decimal('0')
        discount_price = Decimal('0')
        items = CartItem.objects.select_related('product').filter(user=request.user)
        for item in items:
            total_units += item.quantity
            unit_after = Decimal(str(item.product.get_price()))
            unit_before = Decimal(str(item.product.price))
            unit_discount = unit_before * item.product.discount / 100
            after_price += unit_after * item.quantity
            before_price += unit_before * item.quantity
            discount_price += unit_discount * item.quantity
        result = {
            'cart_count': total_units,
            'before_price': before_price,
            'after_price': after_price,
            'discount_price': discount_price,
        }
        cache.set(cache_key, result, 3600)
        return result
    return {'cart_count': 0, 'before_price': 0, 'after_price': 0, 'discount_price': 0}
