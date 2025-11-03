from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CustomUser
from wallet.models import Wallet  # Đảm bảo import từ app wallet

@receiver(post_save, sender=CustomUser)
def create_user_wallet(sender, instance, created, **kwargs):
    """
    Tự động tạo một đối tượng Wallet khi một CustomUser mới được tạo.
    """
    if created:
        Wallet.objects.create(user=instance)