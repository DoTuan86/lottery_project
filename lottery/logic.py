from django.db import transaction
from .models import LotteryResult, Bet
from wallet.models import Transaction
from decimal import Decimal

# Đưa các hằng số tỷ lệ ra đây
DE_RATE = Decimal('70.0')
LO_RATE = Decimal('80.0') / Decimal('23.0')


def process_lottery_results(process_date):
    """
    Hàm logic cốt lõi để tính toán thắng/thua cho một ngày.
    Hàm này có thể được gọi từ bất cứ đâu.
    Trả về: (success_message, error_message)
    """

    # 1. Lấy kết quả
    try:
        result = LotteryResult.objects.get(date=process_date)
    except LotteryResult.DoesNotExist:
        return None, f"Chưa nhập kết quả xổ số cho ngày {process_date}."

    # 2. Lấy tất cả các vé cược đang chờ xử lý
    pending_bets = Bet.objects.filter(date=process_date, status='PENDING')

    if not pending_bets.exists():
        return f"Không có vé cược nào đang chờ xử lý cho ngày {process_date}.", None

    win_count = 0
    lose_count = 0

    # 3. Dùng transaction để đảm bảo an toàn
    try:
        with transaction.atomic():
            for bet in pending_bets:
                winnings = Decimal('0.00')

                # --- Xử lý cược ĐỀ ---
                if bet.bet_type == 'DE':
                    if bet.number == result.de_number:
                        winnings = bet.amount * DE_RATE

                # --- Xử lý cược LÔ ---
                elif bet.bet_type == 'LO':
                    # Đếm số lần số lô xuất hiện
                    hits = result.lo_numbers.count(bet.number)
                    if hits > 0:
                        # Tiền thắng = (tiền cược * tỷ lệ) * số lần về
                        winnings = (bet.amount * LO_RATE) * hits

                # --- Cập nhật kết quả ---
                if winnings > 0:
                    bet.status = 'WON'
                    bet.winnings = winnings
                    win_count += 1

                    # Cộng tiền vào ví người dùng (Đã fix lỗi no-wallet ở lần trước)
                    user_wallet = bet.user.wallet
                    user_wallet.balance += winnings
                    user_wallet.save()

                    # Tạo giao dịch 'WIN'
                    Transaction.objects.create(
                        wallet=user_wallet,
                        amount=winnings,
                        transaction_type='WIN',
                        description=f"Thắng cược {bet.get_bet_type_display()} số {bet.number}"
                    )
                else:
                    bet.status = 'LOST'
                    lose_count += 1

                bet.save()

    except Exception as e:
        # Nếu có bất kỳ lỗi nào, transaction sẽ rollback
        return None, f"Gặp lỗi nghiêm trọng khi xử lý: {e}"

    # 4. Trả về kết quả
    success_msg = f"Hoàn tất cho {process_date}! Thắng: {win_count}, Thua: {lose_count}"
    return success_msg, None