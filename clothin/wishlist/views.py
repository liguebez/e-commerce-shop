from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from urllib.parse import urlparse
from .models import WishlistItem
from main.models import Product


def _login_redirect(request):
    referer = request.META.get('HTTP_REFERER', '/')
    referer_path = urlparse(referer).path or '/'
    return redirect(f"{reverse('users:login')}?next={referer_path}")


def _safe_referer_redirect(request):
    referer = request.META.get('HTTP_REFERER', '/')
    if url_has_allowed_host_and_scheme(referer, allowed_hosts={request.get_host()}):
        return redirect(referer)
    return redirect('/')


@require_POST
def wishlist_add(request, product_id):
    if not request.user.is_authenticated:
        return _login_redirect(request)
    product = get_object_or_404(Product, id=product_id, available=True)
    if not WishlistItem.objects.filter(user=request.user, product=product).exists():
        WishlistItem.objects.create(user=request.user, product=product)

    return _safe_referer_redirect(request)

@require_POST
def wishlist_remove(request, product_id):
    if not request.user.is_authenticated:
        return _login_redirect(request)
    product = get_object_or_404(Product, id=product_id)
    WishlistItem.objects.filter(user=request.user, product=product).delete()

    return _safe_referer_redirect(request)

@login_required
def wishlist_detail(request):
    items = WishlistItem.objects.filter(user=request.user).select_related('product')

    wishlist = [item.product for item in items]

    return render(request, 'wishlist/detail.html', {'wishlist' : wishlist})