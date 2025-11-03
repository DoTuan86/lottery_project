from django.core.management.base import BaseCommand
from django.utils import timezone
# Import hàm logic mới
from lottery.logic import process_lottery_results


# Xóa các import không cần thiết khác (models, Decimal, v.v.)

class Command(BaseCommand):
    help = 'Tính toán thắng/thua cho các vé cược của một ngày cụ thể.'

    def add_arguments(self, parser):
        # (Giữ nguyên hàm add_arguments)
        parser.add_argument('--date', type=str, help='Ngày để tính (YYYY-MM-DD)', default=None)

    def handle(self, *args, **options):
        date_str = options['date']
        if date_str:
            process_date = timezone.datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            process_date = timezone.now().date()

        self.stdout.write(f"Bắt đầu tính toán kết quả cho ngày: {process_date}")

        # === THAY ĐỔI CỐT LÕI ===
        # Gọi hàm logic và nhận kết quả trả về
        success_msg, error_msg = process_lottery_results(process_date)

        # In kết quả ra console
        if error_msg:
            self.stderr.write(f"LỖI: {error_msg}")
        if success_msg:
            self.stdout.write(self.style.SUCCESS(success_msg))
        # === HẾT THAY ĐỔI ===