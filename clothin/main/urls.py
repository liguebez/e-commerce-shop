from django.urls import path
from . import views
from django.views.decorators.cache import cache_page


app_name = 'main'

handler404 = 'main.views.page_not_found'
handler500 = 'main.views.server_error'

urlpatterns = [
    path('', views.index, name='index'),
    path('shop/', views.product_list, name='product_list'),
    path('shop/<slug:category_slug>/', views.product_list, name='product_list_by_category'),
    path('shop/<slug:category_slug>/<slug:product_slug>/', views.product_detail, name='product_detail'),
    path('contact/', views.ContactViewForm.as_view(), name='contact'),
]

