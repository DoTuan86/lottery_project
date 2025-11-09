from django.db import models
from django.conf import settings
from decimal import Decimal


# --- 1. MODEL MỚI: ĐÀI QUAY THƯỞNG ---
class LotteryStation(models.Model):
    REGION_CHOICES = [
        ('NORTH', 'Miền Bắc'),
        ('SOUTH', 'Miền Nam'),
        ('CENTRAL', 'Miền Trung'),
    ]

    name = models.CharField(max_length=100, unique=True, verbose_name="Tên đài")
    identifier = models.SlugField(max_length=100, unique=True, help_text="Ví dụ: mien-bac, tp-hcm, long-an")
    region = models.CharField(max_length=10, choices=REGION_CHOICES, default='NORTH', verbose_name="Vùng miền")

    prize_count = models.PositiveIntegerField(default=27, verbose_name="Số lượng giải (MB=27, MN/MT=18)")

    cutoff_hour = models.PositiveIntegerField(default=18, help_text="Giờ chốt cược (ví dụ: 18 cho 18h00)")

    # TRƯỜNG MỚI (Logic Lịch quay)
    schedule_days = models.CharField(
        max_length=50,
        default="ALL",
        help_text="Các thứ quay (0=T2, 6=CN) cách nhau bằng dấu phẩy, hoặc 'ALL' cho 7 ngày"
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Đài quay thưởng"
        verbose_name_plural = "Các đài quay thưởng"


# --- 2. MODEL KẾT QUẢ (Nâng cấp) ---
class LotteryResult(models.Model):
    station = models.ForeignKey(
        LotteryStation,
        on_delete=models.CASCADE,
        related_name="results",
        verbose_name="Đài"
    )

    date = models.DateField(help_text="Ngày mở thưởng")
    prizes = models.JSONField(help_text="Danh sách các giải")
    de_number = models.CharField(max_length=2, blank=True)
    lo_numbers = models.JSONField(blank=True, null=True)

    class Meta:
        ordering = ['-date', 'station']
        unique_together = ['date', 'station']
        verbose_name = "Kết quả xổ số"
        verbose_name_plural = "Các kết quả xổ số"

    def save(self, *args, **kwargs):
        # Logic này vẫn đúng (GĐB luôn là index 0)
        if self.prizes:
            self.de_number = str(self.prizes[0])[-2:]
            self.lo_numbers = [str(prize)[-2:] for prize in self.prizes]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Kết quả {self.station.name if self.station else 'N/A'} ngày {self.date}"


# --- 3. MODEL VÉ CƯỢC (Nâng cấp) ---
class Bet(models.Model):
    BET_TYPES = [
        ('DE', 'Đề (2 số cuối GĐB)'),
        ('LO', 'Lô (2 số cuối các giải)'),
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

    station = models.ForeignKey(
        LotteryStation,
        on_delete=models.CASCADE,
        related_name="bets",
        verbose_name="Đài",
        null=True,  # Tạm thời cho phép null để di dời
        blank=True
    )

    bet_type = models.CharField(max_length=10, choices=BET_TYPES, verbose_name="Loại cược")
    number = models.CharField(max_length=2, help_text="Số cược (ví dụ: 86, 23)")
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Số tiền cược")
    date = models.DateField(help_text="Cược cho ngày")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    winnings = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['user', 'bet_type', 'number', 'date', 'station']
        verbose_name = "Vé cược"
        verbose_name_plural = "Các vé cược"

    def __str__(self):
        station_name = self.station.name if self.station else 'N/A'
        return f"[{self.user.username}] cược {station_name} {self.number} - {self.amount}đ"