from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction, IntegrityError  # Import thêm IntegrityError
from django.utils import timezone
from .forms import BetForm
from .models import Bet
from wallet.models import Wallet, Transaction
from django.shortcuts import render, redirect


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
    if request.method == 'POST':
        form = BetForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            amount = data['amount']
            bet_type = data['bet_type']
            number = data['number']
            today = timezone.now().date()
            user_wallet = request.user.wallet

            # 1. Kiểm tra số dư
            if user_wallet.balance < amount:
                messages.error(request, "Số dư không đủ để thực hiện cược này.")
                return redirect('place_bet')

                # === NÂNG CẤP LOGIC BẮT ĐẦU TỪ ĐÂY ===
            try:
                # 2. Thử tìm vé cược ĐANG CHỜ XỬ LÝ (PENDING) đã tồn tại
                existing_bet = Bet.objects.filter(
                    user=request.user,
                    bet_type=bet_type,
                    number=number,
                    date=today,
                    status='PENDING'  # Chỉ cộng dồn vào vé đang chờ
                ).first()

                with transaction.atomic():
                    # 3. Trừ tiền khỏi ví (luôn luôn)
                    user_wallet.balance -= amount
                    user_wallet.save()

                    if existing_bet:
                        # --- 4a. ĐÃ CÓ VÉ CŨ -> CỘNG DỒN (GHI THÊM) ---

                        # Cập nhật số tiền vé cược cũ
                        original_amount = existing_bet.amount
                        existing_bet.amount += amount
                        existing_bet.save()

                        # Tạo giao dịch (Transaction) cho việc ghi thêm
                        Transaction.objects.create(
                            wallet=user_wallet,
                            amount=amount,
                            transaction_type='BET',
                            description=f"Ghi thêm {bet_type} số {number} (từ {original_amount}đ)"
                        )

                        messages.success(request,
                                         f"Ghi thêm thành công! Tổng cược cho {bet_type} {number} là: {existing_bet.amount}đ")

                    else:
                        # --- 4b. CHƯA CÓ VÉ -> TẠO VÉ MỚI (LOGIC CŨ) ---

                        # Tạo lịch sử giao dịch (type 'BET')
                        Transaction.objects.create(
                            wallet=user_wallet,
                            amount=amount,
                            transaction_type='BET',
                            description=f"Cược {bet_type} số {number} ngày {today}"
                        )

                        # Tạo vé cược mới
                        Bet.objects.create(
                            user=request.user,
                            bet_type=bet_type,
                            number=number,
                            amount=amount,
                            date=today
                        )

                        messages.success(request, f"Đặt cược thành công cho số {number}!")

                return redirect('place_bet')

            except IntegrityError as e:
                # Bắt lỗi IntegrityError (nếu có vé cược KHÔNG PENDING)
                messages.error(request, f"Lỗi: Không thể cược trùng. (Chi tiết: {e})")
            except Exception as e:
                # Bắt các lỗi chung khác
                messages.error(request, f"Có lỗi xảy ra: {e}")

    else:
        form = BetForm()

    # Hiển thị các vé cược hôm nay của người dùng
    today_bets = Bet.objects.filter(user=request.user, date=timezone.now().date())

    return render(request, 'lottery/place_bet.html', {
        'form': form,
        'today_bets': today_bets
    })