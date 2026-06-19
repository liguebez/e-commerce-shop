from django.urls import path
from . import views
from . import webhooks


app_name = 'payment'

urlpatterns = [
    path('process/', views.payment_process, name='payment_process'),
    path('completed/', views.payment_completed, name='payment_completed'),
    path('cancelled/', views.payment_cancelled, name='payment_cancelled'),
    path('webhook/', webhooks.stripe_webhook, name='payment_webhook'),
]

