from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy

from .forms import ContactForm
from .models import Product, Category
from cart.forms import CartAddProductForm, CartUpdateForm
from django.core.paginator import Paginator
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.edit import FormView
from django.core.cache import cache



def index(request):
    products = Product.objects.all().select_related('category')
    return render(request, 'index/index.html', {'products' : products})

def product_detail(request, category_slug, product_slug):
    category = get_object_or_404(Category, slug=category_slug)
    product = get_object_or_404(Product, slug=product_slug)
    cart_product_form = CartUpdateForm()
    return render(request, 'detail/detail.html', {'product' : product, 'category' : category, 'cart_product_form' : cart_product_form})


def product_list(request, category_slug=None):
    categories = set(Category.objects.filter(products__available=True))
    products = Product.objects.filter(available=True).select_related('category')
    page_number = request.GET.get('page')
    paginator = Paginator(products, 3)
    current_page = paginator.get_page(page_number)
    product_category = None
    if category_slug:
        product_category = get_object_or_404(Category, slug=category_slug)
        paginator = Paginator(products.filter(category=product_category), 10)
        current_page = paginator.get_page(page_number)
    
    return render(request, 'products/products.html', {'current_page' : current_page,
                                                      'categories' : categories,
                                                      'product_category' : product_category})

class ContactViewForm(LoginRequiredMixin, FormView):
    form_class = ContactForm
    template_name = 'contact/contact.html'
    success_url = reverse_lazy('main:index')

    def form_valid(self, form):
        print(form.cleaned_data)
        return super().form_valid(form)
    