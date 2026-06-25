from .models import CartItem
from decimal import Decimal


def cart(request):
    if request.user.is_authenticated:
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
        return {
            'cart_count': total_units,
            'before_price': before_price,
            'after_price': after_price,
            'discount_price': discount_price,
        }
    return {'cart_count': 0, 'before_price': 0, 'after_price': 0, 'discount_price': 0}
