from django.db import models
from django.conf import settings
from decimal import Decimal

class Wallet(models.Model):
    """
    Mỗi người dùng sẽ có MỘT ví.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wallet'
    )
    # Luôn dùng DecimalField cho tiền tệ
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Ví của {self.user.username} (Số dư: {self.balance})"

class Transaction(models.Model):
    """
    Lưu lại lịch sử MỌI thay đổi số dư.
    """
    TRANSACTION_TYPES = [
        ('DEPOSIT', 'Nạp tiền'),
        ('WITHDRAW', 'Rút tiền'),
        ('BET', 'Đặt cược'),
        ('WIN', 'Thắng cược'),
        ('REFUND', 'Hoàn tiền'),
    ]

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    # Mã giao dịch từ bên thứ 3 (cổng thanh toán, nhà cung cấp game)
    external_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.transaction_type}] {self.amount} cho {self.wallet.user.username}"


# ... (Giữ nguyên model Wallet và Transaction) ...

class DepositRequest(models.Model):
    """
    Lưu lại yêu cầu nạp tiền từ người dùng.
    Admin sẽ xem và duyệt các yêu cầu này.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Đang chờ xử lý'),
        ('APPROVED', 'Đã duyệt'),
        ('REJECTED', 'Đã từ chối'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='deposit_requests'
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    # Mã giao dịch (để admin đối chiếu, ví dụ: "VCB 123456")
    transaction_code = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Nhập mã giao dịch ngân hàng hoặc nội dung chuyển khoản"
    )

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(blank=True, null=True, help_text="Ngày admin xử lý")

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[Yêu cầu] {self.user.username} - {self.amount}đ - {self.get_status_display()}"


class WithdrawalRequest(models.Model):
    """
    Lưu lại yêu cầu RÚT tiền từ người dùng.
    """
    # ... (Giữ nguyên các trường user, amount, status, v.v.) ...
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='withdrawal_requests'
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Số tiền rút")

    # --- THÊM 3 TRƯỜNG MỚI NÀY ---
    full_name_cccd = models.CharField(
        max_length=100,
        verbose_name="Tên trên CCCD (Người nhận)"
    )
    bank_name = models.CharField(
        max_length=100,
        verbose_name="Tên ngân hàng"
    )
    account_number = models.CharField(
        max_length=50,
        verbose_name="Số tài khoản"
    )
    # --- KẾT THÚC ---
    STATUS_CHOICES = [
        ('PENDING', 'Đang chờ xử lý'),
        ('APPROVED', 'Đã duyệt'),
        ('REJECTED', 'Đã từ chối'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(blank=True, null=True, help_text="Ngày admin xử lý")

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[Yêu cầu Rút] {self.user.username} - {self.amount}đ - {self.get_status_display()}"