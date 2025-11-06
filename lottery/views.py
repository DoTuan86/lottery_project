from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction, IntegrityError  # Import thêm IntegrityError
from django.utils import timezone
from .forms import BetForm
from .models import Bet
#from wallet.models import Wallet, Transaction
from django.shortcuts import render, redirect
import datetime
from django.shortcuts import get_object_or_404 # <-- Import thêm
from wallet.models import Transaction          # <-- Import thêm

def home_view(request):
    """
    View cho trang chủ (URL gốc).
    """
    if request.user.is_authenticated:
        # Nếu đã đăng nhập, chuyển thẳng đến trang đặt cược
        return redirect('place_bet')

    # Nếu chưa đăng nhập, hiển thị trang chủ
    return render(request, 'home.html')


@login_required
def place_bet_view(request):
    # --- LOGIC MỚI (DÙNG get_current_timezone) ---
    cutoff_hour = 18  # Giờ chốt sổ

    try:
        # 1. Lấy giờ UTC hiện tại
        utc_now = timezone.now()
        # 2. Chuyển đổi sang múi giờ địa phương (từ settings.py)
        local_now = utc_now.astimezone(timezone.get_current_timezone())
    except Exception as e:
        messages.error(request, f"LỖI MÚI GIỜ: {e}. Vui lòng kiểm tra settings.py")
        local_now = utc_now  # Trở về trạng thái cũ để tránh crash

    # 3. Kiểm tra giờ địa phương
    is_after_cutoff = local_now.hour >= cutoff_hour

    if is_after_cutoff:
        bet_date = local_now.date() + datetime.timedelta(days=1)
    else:
        bet_date = local_now.date()
    # --- (Kết thúc logic múi giờ) ---

    if request.method == 'POST':
        form = BetForm(request.POST)
        if form.is_valid():
            # --- LOGIC CƯỢC NHIỀU SỐ ---
            data = form.cleaned_data

            # 'number' LÀ MỘT DANH SÁCH (ví dụ: ['15', '25', '35'])
            number_list = data['number']

            amount_per_bet = data['amount']
            bet_type = data['bet_type']
            user_wallet = request.user.wallet

            # 1. Tính tổng số tiền cần
            total_amount_needed = amount_per_bet * len(number_list)

            # 2. Kiểm tra số dư TỔNG
            if user_wallet.balance < total_amount_needed:
                messages.error(request,
                               f"Số dư không đủ. Bạn cần {total_amount_needed}đ để cược {len(number_list)} số.")
                return redirect('place_bet')

            try:
                # Dùng transaction bao bọc TOÀN BỘ
                with transaction.atomic():

                    # 3. Trừ tổng số tiền khỏi ví MỘT LẦN
                    user_wallet.balance -= total_amount_needed
                    user_wallet.save()

                    bets_created_count = 0
                    bets_updated_count = 0

                    # 4. LẶP qua từng số trong danh sách
                    for number in number_list:

                        # 4a. Tạo giao dịch (Transaction)
                        Transaction.objects.create(
                            wallet=user_wallet,
                            amount=amount_per_bet,
                            transaction_type='BET',
                            description=f"Cược (dàn) {bet_type} số {number} cho ngày {bet_date}"
                        )

                        # 4b. Kiểm tra (ghi thêm)
                        existing_bet = Bet.objects.filter(
                            user=request.user,
                            bet_type=bet_type,
                            number=number,
                            date=bet_date,
                            status='PENDING'
                        ).first()

                        if existing_bet:
                            # --- CỘNG DỒN ---
                            existing_bet.amount += amount_per_bet
                            existing_bet.save()
                            bets_updated_count += 1

                        else:
                            # --- TẠO MỚI ---
                            Bet.objects.create(
                                user=request.user,
                                bet_type=bet_type,
                                number=number,
                                amount=amount_per_bet,
                                date=bet_date,
                                status='PENDING'
                            )
                            bets_created_count += 1

                # 5. Gửi thông báo tổng kết
                messages.success(request,
                                 f"Đặt cược thành công! (Cược mới: {bets_created_count} số, Cược thêm: {bets_updated_count} số). Tổng tiền: {total_amount_needed}đ.")
                return redirect('place_bet')

            except IntegrityError:
                messages.error(request,
                               f"Lỗi: Một trong các số cược (ngày {bet_date}) đã được xử lý. Giao dịch đã bị hủy.")
            except Exception as e:
                messages.error(request, f"Có lỗi xảy ra: {e}")

            # --- KẾT THÚC LOGIC CƯỢC NHIỀU SỐ ---

    else:
        form = BetForm()

    # --- (Logic truy vấn cược hôm nay/ngày mai) ---
    today_date = local_now.date()
    tomorrow_date = today_date + datetime.timedelta(days=1)
    today_bets = Bet.objects.filter(user=request.user, date=today_date)
    tomorrow_bets = Bet.objects.filter(user=request.user, date=tomorrow_date)

    return render(request, 'lottery/place_bet.html', {
        'form': form,
        'today_bets': today_bets,
        'tomorrow_bets': tomorrow_bets,
        'tomorrow_date_for_display': tomorrow_date,
        'today_date_for_display': today_date,
        'is_after_cutoff': is_after_cutoff,
        'bet_date_for_display': bet_date,
    })


@login_required
def delete_bet_view(request, bet_id):
    """
    View để xử lý việc người dùng tự xóa vé cược.
    (Không dùng pytz, dùng timezone.get_current_timezone)
    """
    # 1. Lấy vé cược, đảm bảo nó thuộc về user này
    bet = get_object_or_404(Bet, id=bet_id, user=request.user)

    # 2. Kiểm tra trạng thái cược
    if bet.status != 'PENDING':
        messages.error(request, "Không thể xóa cược đã được xử lý (Thắng/Thua).")
        return redirect('place_bet')

    # 3. Kiểm tra thời gian (SỬA LẠI KHỐI NÀY)
    cutoff_hour = 18
    try:
        # Lấy giờ UTC
        utc_now = timezone.now()
        # Chuyển đổi sang múi giờ hiện tại (từ settings.py)
        local_now = utc_now.astimezone(timezone.get_current_timezone())
    except Exception as e:
        messages.error(request, f"LỖI MÚI GIỜ: {e}. Vui lòng kiểm tra settings.py")
        return redirect('place_bet')
    # --- KẾT THÚC SỬA ---

    # 4. Áp dụng logic kiểm tra:
    # (Giữ nguyên phần này)
    if bet.date == local_now.date():
        if local_now.hour >= cutoff_hour:
            messages.error(request, "Đã qua 18h00, không thể xóa cược của ngày hôm nay.")
            return redirect('place_bet')

    # 5. Tiến hành hoàn tiền và xóa (nếu mọi thứ hợp lệ)
    # (Giữ nguyên phần này)
    try:
        with transaction.atomic():
            # 5a. Hoàn tiền vào ví
            wallet = request.user.wallet
            wallet.balance += bet.amount
            wallet.save()

            # 5b. Tạo giao dịch 'REFUND'
            Transaction.objects.create(
                wallet=wallet,
                amount=bet.amount,
                transaction_type='REFUND',
                description=f"Hoàn tiền (hủy cược {bet.bet_type} {bet.number})"
            )

            # 5c. Xóa vé cược
            bet_info = f"{bet.bet_type} {bet.number}"
            bet_amount = bet.amount
            bet.delete()

        messages.success(request, f"Đã xóa cược {bet_info} và hoàn {bet_amount}đ vào ví.")

    except Exception as e:
        messages.error(request, f"Lỗi khi xóa cược: {e}")

    return redirect('place_bet')