from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Category, Product

@receiver([post_save, post_delete], sender=Category)
def invalidate_category_caches(sender, instance, **kwargs):
    cache.delete('main:v1:categories:all')


@receiver([post_save, post_delete], sender=Product)
def invalidate_homepage_cache(sender, instance, **kwargs):
    cache.delete('main:v1:homepage_products')
