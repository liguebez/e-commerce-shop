from .models import CartItem
from decimal import Decimal

def cart(request):
    if request.user.is_authenticated:
        # Choose: distinct lines vs total units. Here: total units.
        total_units = 0
        for item in CartItem.objects.filter(user=request.user):
            total_units += item.quantity
        return {'cart_count': total_units}
    return {'cart_count': 0}

def cart_total_price(request):
    if request.user.is_authenticated:
        # Choose: distinct lines vs total units. Here: total units.
        after_price = 0 
        before_price = 0
        discount_price = 0
        cart = CartItem.objects.select_related('product').filter(user=request.user)
        for item in cart:
            unit_after = Decimal(item.product.get_price())
            unit_before = Decimal(item.product.price)
            unit_discount = Decimal(item.product.price * item.product.discount/100)

            after_price += unit_after * item.quantity
            discount_price += unit_discount * item.quantity
            before_price += unit_before * item.quantity

        return {'before_price': before_price, 'after_price': after_price, 'discount_price' : discount_price}
    return {'before_price': 0, 'after_price': 0, 'discount_price' : 0}