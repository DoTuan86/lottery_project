from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('dat-cuoc/', views.place_bet_view, name='place_bet'),
    path('xoa-cuoc/<int:bet_id>/', views.delete_bet_view, name='delete_bet'),
]