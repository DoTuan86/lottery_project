from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    """Model người dùng tùy chỉnh"""

    # Bạn có thể thêm các trường như SĐT, ngày sinh, CMND...
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.username

    # Sau khi tạo model này, đừng quên tạo 'Wallet' cho user
    # (Sử dụng tín hiệu signals.py)