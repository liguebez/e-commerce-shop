from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy

from .forms import ContactForm
from .models import Product, Category
from cart.forms import CartAddProductForm, CartUpdateForm
from django.core.paginator import Paginator
from django.views.generic.edit import FormView
from django.core.cache import cache
from django.db.models import Q

from django.core.mail import EmailMessage
from django.conf import settings
from django.contrib import messages


def index(request):
    products = Product.objects.filter(available=True).select_related('category')
    return render(request, 'index/index.html', {'products' : products})

def product_detail(request, category_slug, product_slug):
    category = get_object_or_404(Category, slug=category_slug)
    product = get_object_or_404(Product, slug=product_slug, category=category)
    cart_product_form = CartUpdateForm()
    return render(request, 'detail/detail.html', {'product' : product, 'category' : category, 'cart_product_form' : cart_product_form})


SORT_OPTIONS = {
    'price_asc': 'price',
    'price_desc': '-price',
    'newest': '-date_create',
}

def product_list(request, category_slug=None):
    sort_key = request.GET.get('sort', 'newest')
    order_by = SORT_OPTIONS.get(sort_key, '-date_create')
    query = request.GET.get('q', '').strip()
    categories = Category.objects.all()
    products = Product.objects.filter(available=True).select_related('category').order_by(order_by)

    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )

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
                                                      'product_category' : product_category,
                                                      'query': query,
                                                      'current_sort': sort_key})

class ContactViewForm(FormView):
    form_class = ContactForm
    template_name = 'contact/contact.html'
    success_url = reverse_lazy('main:contact')

    def form_valid(self, form):
        cd = form.cleaned_data
        try:
            email = EmailMessage(
                subject=f'Contact form: message from {cd["name"]}',
                body=cd['content'],
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[settings.CONTACT_EMAIL],
                reply_to=[cd['email']],
            )
            sent = email.send()
            if sent:
                messages.success(self.request, 'Your message has been sent. We will get back to you shortly.')
            else:
                messages.error(self.request, 'Sorry, we could not send your message. Please try again later.')
        except Exception:
            messages.error(self.request, 'Sorry, we could not send your message. Please try again later.')
        return super().form_valid(form)

    def get_initial(self):

        initial = super().get_initial()
        if self.request.user.is_authenticated:
            initial['email'] = self.request.user.email
            initial['name'] = self.request.user.get_full_name() or self.request.user.username
            
        return initial
    

def page_not_found(request, exception):
    return render(request, '404.html', status=404)

def server_error(request):
    return render(request, '500.html', status=500)