from .models import WishlistItem
from django.core.cache import cache



def wishlist(request):
    if request.user.is_authenticated:
        
        cache_key = f'wishlist:v1:count:user:{request.user.id}'
        count = cache.get(cache_key)
        if count is None:
            count = WishlistItem.objects.filter(user=request.user).count()
            cache.set(f'wishlist:v1:count:user:{request.user.id}', count, 3600)
        return {'wishlist_count': count}
    
    return {'wishlist_count': 0}
