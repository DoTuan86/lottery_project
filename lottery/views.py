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
    # --- LOGIC MỚI ĐỂ XÁC ĐỊNH GIỜ ĐỊA PHƯƠNG ---
    cutoff_hour = 12  # Giờ chốt sổ

    # 1. Lấy giờ UTC hiện tại
    utc_now = timezone.now()

    # 2. Chuyển đổi sang múi giờ địa phương (GMT+7)
    try:
        local_now = utc_now.astimezone(timezone.get_current_timezone())
    except Exception as e:
        messages.error(request, f"LỖI MÚI GIỜ: {e}. Vui lòng kiểm tra settings.py")
        local_now = utc_now

        # 3. Kiểm tra giờ địa phương
    is_after_cutoff = local_now.hour >= cutoff_hour

    if is_after_cutoff:
        bet_date = local_now.date() + datetime.timedelta(days=1)
    else:
        bet_date = local_now.date()
    # --- KẾT THÚC LOGIC MỚI ---

    if request.method == 'POST':
        form = BetForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            amount = data['amount']
            bet_type = data['bet_type']
            number = data['number']
            user_wallet = request.user.wallet

            if user_wallet.balance < amount:
                messages.error(request, "Số dư không đủ.")
                return redirect('place_bet')

            try:
                # (Toàn bộ logic POST không thay đổi)
                with transaction.atomic():
                    existing_bet = Bet.objects.filter(
                        user=request.user,
                        bet_type=bet_type,
                        number=number,
                        date=bet_date,
                        status='PENDING'
                    ).first()

                    if existing_bet:
                        # --- PATH A: CỘNG DỒN ---
                        original_amount = existing_bet.amount
                        existing_bet.amount += amount
                        existing_bet.save()
                        user_wallet.balance -= amount
                        user_wallet.save()
                        Transaction.objects.create(
                            wallet=user_wallet,
                            amount=amount,
                            transaction_type='BET',
                            description=f"Ghi thêm {bet_type} {number} ngày {bet_date} (từ {original_amount}đ)"
                        )
                        messages.success(request,
                                         f"Ghi thêm thành công! Tổng cược {bet_type} {number} ngày {bet_date} là: {existing_bet.amount}đ")

                    else:
                        # --- PATH B: TẠO MỚI ---
                        Bet.objects.create(
                            user=request.user,
                            bet_type=bet_type,
                            number=number,
                            amount=amount,
                            date=bet_date,
                            status='PENDING'
                        )
                        user_wallet.balance -= amount
                        user_wallet.save()
                        Transaction.objects.create(
                            wallet=user_wallet,
                            amount=amount,
                            transaction_type='BET',
                            description=f"Cược {bet_type} số {number} cho ngày {bet_date}"
                        )
                        messages.success(request, f"Đặt cược thành công cho số {number} (Ngày cược: {bet_date})!")

                return redirect('place_bet')

            except IntegrityError:
                messages.error(request,
                               f"Lỗi: Không thể đặt cược cho số {number} (ngày {bet_date}). Có thể vé cược này đã được xử lý.")
            except Exception as e:
                messages.error(request, f"Có lỗi xảy ra: {e}")

    else:
        form = BetForm()

    # --- THAY ĐỔI LOGIC TRUY VẤN Ở ĐÂY ---

    # 1. Lấy ngày hôm nay và ngày mai (dựa trên giờ địa phương)
    today_date = local_now.date()
    tomorrow_date = today_date + datetime.timedelta(days=1)

    # 2. Lấy cược của HÔM NAY
    today_bets = Bet.objects.filter(user=request.user, date=today_date)

    # 3. Lấy cược của NGÀY MAI
    tomorrow_bets = Bet.objects.filter(user=request.user, date=tomorrow_date)

    # --- KẾT THÚC THAY ĐỔI ---

    return render(request, 'lottery/place_bet.html', {
        'form': form,
        'today_bets': today_bets,
        'tomorrow_bets': tomorrow_bets,  # <-- GỬI QUA TEMPLATE
        'tomorrow_date_for_display': tomorrow_date,  # <-- GỬI QUA TEMPLATE
        'is_after_cutoff': is_after_cutoff,
        'bet_date_for_display': bet_date,
        'today_date_for_display': today_date,
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