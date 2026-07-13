from django.db import models
from django.urls import reverse
from django.core.validators import MinValueValidator, MaxValueValidator

# Create your models here.

class Category(models.Model):
    name = models.CharField(max_length=30, unique=True)
    slug = models.SlugField(auto_created=True, unique=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse("main:product_list_by_category", kwargs={"category_slug": self.slug})
    

class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    name = models.CharField(max_length=25, unique=True)
    slug = models.SlugField(auto_created=True, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.IntegerField(default=0, blank=True,
                                   validators=[MinValueValidator(0), MaxValueValidator(100)])
    image = models.ImageField(upload_to='products/%Y/%m/%d/')
    description = models.TextField(blank=True, null=True)
    available = models.BooleanField(default=True)
    date_create = models.DateTimeField(auto_now_add=True)
    stock = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('main:product_detail', kwargs={"category_slug": self.category.slug,
                                                 "product_slug": self.slug})
    
    def get_price(self):
        return self.price - ((self.price * self.discount) / 100)