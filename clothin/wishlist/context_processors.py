from .models import WishlistItem

def wishlist(request):
    if request.user.is_authenticated:
        items = (WishlistItem.objects.select_related('product').filter(user=request.user))
        return {'wishlist_count': len(items)}
    return {'wishlist_count': 0}