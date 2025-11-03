from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser
from wallet.models import Wallet  # Import từ app wallet


# Định nghĩa một "Inline" để hiển thị Wallet NGAY BÊN TRONG trang CustomUser
class WalletInline(admin.StackedInline):
    model = Wallet
    can_delete = False  # Không cho phép xóa ví từ trang user
    verbose_name_plural = 'Ví tiền của người dùng'
    # Bạn có thể làm cho số dư chỉ được đọc
    readonly_fields = ('balance',)


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    # Thêm 'WalletInline' vào trang admin của User
    inlines = (WalletInline,)

    # Thêm các trường tùy chỉnh (nếu có) vào list_display
    list_display = ('username', 'email', 'phone_number', 'is_staff')

    # Thêm các trường tùy chỉnh vào khu vực chỉnh sửa
    # Chúng ta kế thừa UserAdmin.fieldsets và thêm vào
    fieldsets = UserAdmin.fieldsets + (
        ('Thông tin bổ sung', {'fields': ('phone_number', 'date_of_birth')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Thông tin bổ sung', {'fields': ('phone_number', 'date_of_birth')}),
    )