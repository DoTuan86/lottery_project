from django.contrib import admin, messages
from .models import LotteryResult, Bet
# Import hàm logic mới của chúng ta
from .logic import process_lottery_results


@admin.register(LotteryResult)
class LotteryResultAdmin(admin.ModelAdmin):
    list_display = ('date', 'de_number', 'prizes_count')
    readonly_fields = ('de_number', 'lo_numbers')
    search_fields = ['date']

    # === THÊM PHẦN NÀY ===

    # 1. Thêm 'run_calculation' vào danh sách actions
    actions = ['run_calculation']

    # 2. Định nghĩa action
    @admin.action(description="Tính toán thắng/thua cho các ngày đã chọn")
    def run_calculation(self, request, queryset):
        """
        Admin Action để chạy tính toán thắng/thua.
        'queryset' là danh sách các đối tượng LotteryResult mà admin đã tick chọn.
        """

        success_count = 0
        error_count = 0

        # Lặp qua từng 'Kết quả' mà admin đã chọn
        for result_obj in queryset:
            # Gọi hàm logic
            success_msg, error_msg = process_lottery_results(result_obj.date)

            # Hiển thị thông báo cho admin
            if error_msg:
                # self.message_user là cách hiển thị thông báo trong admin
                self.message_user(request, f"Lỗi ngày {result_obj.date}: {error_msg}", messages.ERROR)
                error_count += 1
            if success_msg:
                self.message_user(request, f"Kết quả ngày {result_obj.date}: {success_msg}", messages.INFO)
                success_count += 1

        # Báo cáo tổng kết
        self.message_user(request, f"Hoàn tất xử lý. Thành công: {success_count} ngày, Lỗi: {error_count} ngày.",
                          messages.SUCCESS)

    # === KẾT THÚC PHẦN THÊM ===

    def prizes_count(self, obj):
        if obj.prizes:
            return len(obj.prizes)
        return 0

    prizes_count.short_description = "Số lượng giải"


@admin.register(Bet)
class BetAdmin(admin.ModelAdmin):
    # (Giữ nguyên code của BetAdmin)
    list_display = ('user', 'bet_type', 'number', 'amount', 'date', 'status', 'winnings')
    list_filter = ('date', 'status', 'bet_type')
    search_fields = ('user__username', 'number')
    readonly_fields = ('winnings',)