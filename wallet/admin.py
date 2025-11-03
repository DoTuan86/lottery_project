from django.contrib import admin, messages
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django import forms
from .models import Wallet, Transaction, DepositRequest, WithdrawalRequest
from decimal import Decimal
from django.utils import timezone
#from django.utils.html import format_html


# --- 1. Tạo một Form để hỏi Admin muốn nạp bao nhiêu ---
class DepositForm(forms.Form):
    amount = forms.DecimalField(
        label='Số tiền nạp',
        min_value=Decimal('10000'),  # Tối thiểu 10,000
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'placeholder': 'Ví dụ: 500000'})
    )
    description = forms.CharField(
        label='Mô tả (Tùy chọn)',
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Nạp tiền khuyến mãi, nạp tay...'})
    )


# --- 2. Đăng ký Wallet Admin với Action tùy chỉnh ---
@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'updated_at')
    search_fields = ('user__username', 'user__email')

    # QUAN TRỌNG: Ngăn admin sửa số dư bằng tay
    readonly_fields = ('user', 'balance', 'created_at', 'updated_at')

    # Thêm Action "Nạp tiền"
    actions = ['deposit_funds']

    @admin.action(description="Nạp tiền cho các ví đã chọn")
    def deposit_funds(self, request, queryset):
        """
        Đây là Action tùy chỉnh để nạp tiền.
        Nó sẽ hiển thị một trang trung gian để nhập số tiền.
        """
        form = None

        # Bước 3: Admin đã nhập số tiền và bấm "Xác nhận"
        if 'apply' in request.POST:
            form = DepositForm(request.POST)

            if form.is_valid():
                amount = form.cleaned_data['amount']
                description = form.cleaned_data['description']

                count = 0
                try:
                    # Dùng transaction để đảm bảo an toàn tuyệt đối
                    with transaction.atomic():
                        for wallet in queryset:
                            # 1. Cộng tiền vào ví
                            wallet.balance += amount
                            wallet.save()

                            # 2. Tạo lịch sử giao dịch
                            Transaction.objects.create(
                                wallet=wallet,
                                amount=amount,  # Số tiền CỘNG vào
                                transaction_type='DEPOSIT',
                                description=f"Admin nạp: {description}"
                            )
                            count += 1

                    # Thông báo thành công
                    self.message_user(request, f"Đã nạp {amount}đ thành công cho {count} ví.", messages.SUCCESS)
                    return HttpResponseRedirect(request.get_full_path())

                except Exception as e:
                    self.message_user(request, f"Gặp lỗi khi nạp tiền: {e}", messages.ERROR)

        # Bước 2: Admin vừa chọn action, hiển thị form để nhập số tiền
        if not form:
            form = DepositForm()

        # Render trang trung gian
        return render(request, 'admin/deposit_intermediate.html', {
            'wallets': queryset,
            'form': form,
            'title': 'Nạp tiền vào ví'
        })


# --- 3. (Nên làm) Đăng ký Transaction Admin để xem lịch sử ---
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('wallet', 'amount', 'transaction_type', 'timestamp', 'description')
    list_filter = ('transaction_type', 'timestamp')
    search_fields = ('wallet__user__username',)
    readonly_fields = ('wallet', 'amount', 'transaction_type', 'description', 'external_id')


# === THÊM ADMIN CHO DEPOSIT REQUEST ===
@admin.register(DepositRequest)
class DepositRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'status', 'transaction_code', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'transaction_code')

    # Chỉ cho admin xem, không cho sửa
    readonly_fields = ('user', 'amount', 'transaction_code', 'created_at', 'processed_at')

    # Thêm 2 actions
    actions = ['approve_deposits', 'reject_deposits']

    @admin.action(description="Duyệt các yêu cầu nạp tiền đã chọn")
    def approve_deposits(self, request, queryset):
        # Lọc ra các yêu cầu đang chờ
        pending_requests = queryset.filter(status='PENDING')

        count = 0
        try:
            with transaction.atomic():
                for req in pending_requests:
                    wallet = req.user.wallet

                    # 1. Cộng tiền vào ví
                    wallet.balance += req.amount
                    wallet.save()

                    # 2. Tạo lịch sử giao dịch
                    Transaction.objects.create(
                        wallet=wallet,
                        amount=req.amount,
                        transaction_type='DEPOSIT',
                        description=f"Admin duyệt yêu cầu nạp tiền #{req.id}"
                    )

                    # 3. Cập nhật trạng thái yêu cầu
                    req.status = 'APPROVED'
                    req.processed_at = timezone.now()
                    req.save()

                    count += 1

            self.message_user(request, f"Đã duyệt thành công {count} yêu cầu nạp tiền.", messages.SUCCESS)

        except Exception as e:
            self.message_user(request, f"Gặp lỗi khi duyệt: {e}", messages.ERROR)

    @admin.action(description="Từ chối các yêu cầu nạp tiền đã chọn")
    def reject_deposits(self, request, queryset):
        # Lọc ra các yêu cầu đang chờ
        pending_requests = queryset.filter(status='PENDING')

        count = 0
        for req in pending_requests:
            req.status = 'REJECTED'
            req.processed_at = timezone.now()
            req.save()
            count += 1

        self.message_user(request, f"Đã từ chối {count} yêu cầu nạp tiền.", messages.INFO)


# ... (Giữ nguyên các Admin khác) ...

@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    # ... (Giữ nguyên list_display, list_filter, search_fields, readonly_fields) ...
    list_display = (
        'user',
        'amount',
        'status',
        'created_at',
        'full_name_cccd',
        'bank_name',
        'account_number',
    )
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'account_number', 'full_name_cccd')
    readonly_fields = (
        'user',
        'amount',
        'created_at',
        'processed_at',
        'full_name_cccd',
        'bank_name',
        'account_number',
    )

    actions = ['approve_withdrawals', 'reject_withdrawals']

    @admin.action(description="Duyệt các yêu cầu RÚT tiền đã chọn (Đã chuyển tiền)")
    def approve_withdrawals(self, request, queryset):
        # Admin phải TỰ CHUYỂN TIỀN TRƯỚC khi bấm nút này

        pending_requests = queryset.filter(status='PENDING')
        success_count = 0
        fail_count = 0

        try:
            # Dùng transaction để đảm bảo an toàn
            with transaction.atomic():
                for req in pending_requests:
                    wallet = req.user.wallet

                    # 1. Kiểm tra lại xem user CÒN đủ tiền không
                    if wallet.balance >= req.amount:
                        # 2. TRỪ TIỀN (Chuyển logic về đây)
                        wallet.balance -= req.amount
                        wallet.save()

                        # 3. Tạo giao dịch 'WITHDRAW'
                        Transaction.objects.create(
                            wallet=wallet,
                            amount=req.amount,
                            transaction_type='WITHDRAW',
                            description=f"Admin duyệt yêu cầu rút tiền #{req.id}"
                        )

                        # 4. Cập nhật trạng thái yêu cầu
                        req.status = 'APPROVED'
                        req.processed_at = timezone.now()
                        req.save()

                        success_count += 1
                    else:
                        # Nếu user không còn đủ tiền (ví dụ: đã cược thua)
                        fail_count += 1
                        req.status = 'REJECTED'  # Tự động từ chối
                        req.processed_at = timezone.now()
                        req.save()
                        # Báo lỗi cụ thể cho admin
                        self.message_user(request,
                                          f"Từ chối YC #{req.id} của {req.user.username}: Không đủ số dư (cần {req.amount}, có {wallet.balance}).",
                                          messages.ERROR)

            if success_count > 0:
                self.message_user(request, f"Đã duyệt và trừ tiền thành công {success_count} yêu cầu.",
                                  messages.SUCCESS)
            if fail_count > 0:
                self.message_user(request, f"Đã từ chối {fail_count} yêu cầu do không đủ số dư.", messages.WARNING)

        except Exception as e:
            self.message_user(request, f"Gặp lỗi nghiêm trọng khi duyệt: {e}", messages.ERROR)

    @admin.action(description="Từ chối các yêu cầu RÚT tiền")
    def reject_withdrawals(self, request, queryset):
        pending_requests = queryset.filter(status='PENDING')

        # --- ĐƠN GIẢN HÓA LOGIC ---
        # Không cần hoàn tiền nữa, vì tiền chưa bao giờ bị trừ
        count = 0
        for req in pending_requests:
            req.status = 'REJECTED'
            req.processed_at = timezone.now()
            req.save()
            count += 1
        # --- KẾT THÚC ---

        self.message_user(request, f"Đã từ chối {count} yêu cầu rút tiền.", messages.INFO)