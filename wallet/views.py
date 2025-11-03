from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
#from django.db import transaction
from .forms import DepositRequestForm, WithdrawalRequestForm
from .models import DepositRequest, WithdrawalRequest, Transaction


@login_required
def request_deposit_view(request):
    if request.method == 'POST':
        form = DepositRequestForm(request.POST)
        if form.is_valid():
            # Tạo yêu cầu nhưng chưa lưu
            deposit_request = form.save(commit=False)
            deposit_request.user = request.user  # Gán user hiện tại
            deposit_request.save()

            messages.success(request, "Yêu cầu nạp tiền của bạn đã được gửi. Vui lòng chờ admin xử lý.")
            return redirect('request_deposit')
    else:
        form = DepositRequestForm()

    # Hiển thị các yêu cầu nạp tiền gần đây
    recent_requests = DepositRequest.objects.filter(user=request.user)[:5]

    return render(request, 'wallet/request_deposit.html', {
        'form': form,
        'recent_requests': recent_requests
    })


# ... (giữ các import) ...

@login_required
def request_withdrawal_view(request):
    wallet = request.user.wallet

    if request.method == 'POST':
        form = WithdrawalRequestForm(request.POST, wallet=wallet)
        if form.is_valid():
            # Form đã kiểm tra xem user CÓ đủ tiền tại thời điểm này.
            # Chúng ta sẽ KHÔNG trừ tiền ở đây nữa.

            try:
                # --- BỎ LOGIC CŨ ---
                # Bỏ transaction.atomic
                # Bỏ wallet.balance -= amount
                # Bỏ wallet.save()
                # Bỏ Transaction.objects.create(...)
                # --- KẾT THÚC ---

                # 3. Chỉ tạo yêu cầu rút tiền
                withdrawal_request = form.save(commit=False)
                withdrawal_request.user = request.user
                withdrawal_request.save()

                messages.success(request, "Yêu cầu rút tiền đã được gửi. Admin sẽ xử lý và chuyển tiền cho bạn.")
                return redirect('request_withdrawal')

            except Exception as e:
                # Bắt lỗi nếu có
                messages.error(request, f"Có lỗi xảy ra: {e}")
    else:
        form = WithdrawalRequestForm(wallet=wallet)

    recent_requests = WithdrawalRequest.objects.filter(user=request.user)[:5]

    return render(request, 'wallet/request_withdrawal.html', {
        'form': form,
        'recent_requests': recent_requests,
    })
