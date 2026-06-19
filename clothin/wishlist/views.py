from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import WishlistItem
from main.models import Product
# Create your views here.

@login_required
@require_POST
def wishlist_add(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if not WishlistItem.objects.filter(user=request.user, product=product).exists():
        WishlistItem.objects.create(user=request.user, product=product)
    
    return redirect('wishlist:wishlist_detail')

@login_required
@require_POST
def wishlist_remove(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    WishlistItem.objects.filter(user=request.user, product=product).delete()

    return redirect('wishlist:wishlist_detail')

@login_required
def wishlist_detail(request):

    items = (WishlistItem.objects.filter(user=request.user))
    
    wishlist = []
    
    for item in items:
        wishlist.append(item.product)

    return render(request, 'wishlist/detail.html', {'wishlist' : wishlist})