from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('dang-ky/', views.register_view, name='register'),
    # Thêm các URL cho đăng nhập/đăng xuất (nếu bạn dùng admin, nó có sẵn)
    path('dang-nhap/', auth_views.LoginView.as_view(template_name='users/login.html'), name='login'),
    path('dang-xuat/', views.custom_logout_view, name='logout'),
]