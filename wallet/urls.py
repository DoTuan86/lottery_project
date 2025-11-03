from django.urls import path
from . import views

urlpatterns = [
    path('nap-tien/', views.request_deposit_view, name='request_deposit'),
    path('rut-tien/', views.request_withdrawal_view, name='request_withdrawal'),
]