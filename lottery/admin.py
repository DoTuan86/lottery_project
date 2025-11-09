from django.contrib import admin, messages
from .models import LotteryResult, Bet, LotteryStation  # Thêm LotteryStation
from .logic import process_lottery_results


# Đăng ký model mới
@admin.register(LotteryStation)
class LotteryStationAdmin(admin.ModelAdmin):
    list_display = ('name', 'identifier', 'region', 'prize_count', 'cutoff_hour', 'schedule_days')
    list_filter = ('region',)
    search_fields = ('name', 'identifier')


# Nâng cấp model cũ
@admin.register(LotteryResult)
class LotteryResultAdmin(admin.ModelAdmin):
    list_display = ('date', 'station', 'de_number', 'prizes_count')
    list_filter = ('date', 'station')
    readonly_fields = ('de_number', 'lo_numbers')
    search_fields = ['date']
    actions = ['run_calculation']

    @admin.action(description="Tính toán thắng/thua cho các kết quả đã chọn")
    def run_calculation(self, request, queryset):
        success_count = 0
        error_count = 0

        for result_obj in queryset:
            if result_obj.station:
                success_msg, error_msg = process_lottery_results(
                    result_obj.date,
                    result_obj.station.id
                )

                if error_msg:
                    self.message_user(request, f"Lỗi ngày {result_obj.date} ({result_obj.station.name}): {error_msg}",
                                      messages.ERROR)
                    error_count += 1
                if success_msg:
                    self.message_user(request,
                                      f"Kết quả ngày {result_obj.date} ({result_obj.station.name}): {success_msg}",
                                      messages.INFO)
                    success_count += 1
            else:
                self.message_user(request, f"Lỗi: Kết quả ngày {result_obj.date} thiếu đài.", messages.ERROR)
                error_count += 1

        self.message_user(request, f"Hoàn tất xử lý. Thành công: {success_count}, Lỗi: {error_count}.",
                          messages.SUCCESS)

    def prizes_count(self, obj):
        if obj.prizes:
            return len(obj.prizes)
        return 0

    prizes_count.short_description = "Số lượng giải"


@admin.register(Bet)
class BetAdmin(admin.ModelAdmin):
    list_display = ('user', 'station', 'bet_type', 'number', 'amount', 'date', 'status', 'winnings', 'created_at')
    list_filter = ('date', 'status', 'bet_type', 'station')
    search_fields = ('user__username', 'number', 'station__name')
    readonly_fields = ('winnings', 'created_at')