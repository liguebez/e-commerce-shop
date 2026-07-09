from django.contrib import admin

# Register your models here.
from .models import Product, Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ['name']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    list_display = ("id", "name", 'slug', "price", 'discount', "category", "available", 'image', 'description', 'date_create', 'stock')
    list_editable = ("name", 'slug', "price", "category", 'discount', "available", 'image', 'description', 'stock')
    list_filter = ['category', 'available'] 
    search_fields = ['name', 'description'] 