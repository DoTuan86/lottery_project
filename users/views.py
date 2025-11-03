from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib import messages
from .forms import CustomUserCreationForm


def register_view(request):
    if request.user.is_authenticated:
        return redirect('place_bet')  # Nếu đã đăng nhập, về trang đặt cược

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()  # Lưu user, signal sẽ tự động tạo ví
            login(request, user)  # Tự động đăng nhập cho user sau khi đăng ký
            messages.success(request, "Đăng ký thành công!")
            return redirect('place_bet')  # Về trang đặt cược
        else:
            messages.error(request, "Vui lòng sửa các lỗi bên dưới.")
    else:
        form = CustomUserCreationForm()

    return render(request, 'users/register.html', {'form': form})

# === THÊM HÀM MỚI NÀY VÀO CUỐI FILE ===
def custom_logout_view(request):
    """
    View đăng xuất tùy chỉnh để chấp nhận GET request.
    """
    logout(request)
    # Chuyển hướng về trang chủ (tên 'home' ta đã đặt ở bước trước)
    return redirect('home')