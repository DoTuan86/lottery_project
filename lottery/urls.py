from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('dat-cuoc/', views.place_bet_view, name='place_bet'),
    # Thêm các view khác (kết quả, lịch sử...) ở đây
]