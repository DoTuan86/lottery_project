from django.db import models
from django.conf import settings
from decimal import Decimal


class LotteryResult(models.Model):
    """
    Lưu kết quả XSMB mỗi ngày.
    Admin sẽ nhập 27 giải vào trường 'prizes'.
    """
    date = models.DateField(unique=True, help_text="Ngày mở thưởng")

    # Chúng ta dùng JSONField để lưu danh sách 27 giải
    # Admin sẽ nhập vào một list: ["12345", "67890", "11111", ...]
    prizes = models.JSONField(
        help_text="Danh sách 27 giải, từ GĐB đến giải 7. Ví dụ: [\"54321\", \"12345\", ...]"
    )

    # 2 trường này sẽ được tự động tính toán khi lưu
    de_number = models.CharField(
        max_length=2,
        blank=True,
        help_text="2 số cuối giải đặc biệt (tự động cập nhật)"
    )
    lo_numbers = models.JSONField(
        blank=True,
        null=True,
        help_text="Danh sách 27 số lô (tự động cập nhật)"
    )

    class Meta:
        ordering = ['-date']

    def save(self, *args, **kwargs):
        """
        Ghi đè hàm save để tự động trích xuất số 'Đề' và 'Lô'
        từ danh sách 27 giải.
        """
        if self.prizes and len(self.prizes) == 27:
            # Giải đặc biệt là giải đầu tiên trong danh sách
            special_prize = str(self.prizes[0])
            self.de_number = special_prize[-2:]

            # Lô là 2 số cuối của TẤT CẢ 27 giải
            self.lo_numbers = [str(prize)[-2:] for prize in self.prizes]

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Kết quả ngày {self.date} (Đề: {self.de_number})"


class Bet(models.Model):
    """
    Lưu lại từng vé cược của người dùng.
    """
    BET_TYPES = [
        ('DE', 'Đề (2 số cuối GĐB)'),
        ('LO', 'Lô (2 số cuối 27 giải)'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Chờ xử lý'),
        ('WON', 'Thắng'),
        ('LOST', 'Thua'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bets'
    )
    bet_type = models.CharField(max_length=2, choices=BET_TYPES)
    number = models.CharField(max_length=2, help_text="Số cược (ví dụ: 86, 23)")

    # Số tiền người dùng đặt cược
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    # Ngày mà vé cược này áp dụng
    date = models.DateField(help_text="Cược cho ngày")

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')

    # Số tiền thắng (nếu thắng)
    winnings = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        # Đảm bảo người dùng không cược trùng lặp (cùng 1 số, cùng 1 loại, cùng 1 ngày)
        unique_together = ['user', 'bet_type', 'number', 'date']

    def __str__(self):
        return f"[{self.user.username}] cược {self.get_bet_type_display()}: {self.number} - {self.amount}đ"