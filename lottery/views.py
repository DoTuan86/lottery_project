from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import transaction as db_transaction, IntegrityError  # 1. Sửa lỗi trùng tên
from django.db.models import Q
from django.utils import timezone
from .models import Bet, LotteryStation, LotteryResult  # 2. Sửa import
from wallet.models import Transaction  # 3. Sửa import
from .forms import BetForm, ImageUploadForm
from .logic import get_results_from_gemini, process_lottery_results
import datetime


# (Định nghĩa hàm lấy giờ địa phương)
def get_local_now():
    try:
        # (Đảm bảo settings.TIME_ZONE = 'Asia/Ho_Chi_Minh')
        return timezone.now().astimezone(timezone.get_current_timezone())
    except Exception as e:
        print(f"LỖI MÚI GIỜ: {e}. Dùng UTC.")
        return timezone.now()


# (View 'home_view' và 'is_admin' giữ nguyên)
def home_view(request):
    if request.user.is_authenticated:
        return redirect('place_bet')
    return render(request, 'home.html')


def is_admin(user):
    return user.is_authenticated and user.is_superuser


# --- VIEW ĐẶT CƯỢC (ĐÃ SỬA LỖI LOGIC LỌC ĐÀI) ---
@login_required
def place_bet_view(request):
    local_now = get_local_now()
    today_date = local_now.date()
    tomorrow_date = today_date + datetime.timedelta(days=1)

    # --- LỌC ĐÀI (LOGIC MỚI) ---
    today_day_of_week = str(today_date.weekday())
    tomorrow_day_of_week = str(tomorrow_date.weekday())

    # 1. Lấy các đài CÓ LỊCH quay hôm nay VÀ CHƯA TỚI GIỜ CHỐT
    stations_today_open = LotteryStation.objects.filter(
        (Q(schedule_days="ALL") | Q(schedule_days__contains=today_day_of_week)) &
        Q(cutoff_hour__gt=local_now.hour)  # Lớn hơn giờ hiện tại
    )

    # 2. Lấy các đài CÓ LỊCH quay ngày mai
    stations_tomorrow = LotteryStation.objects.filter(
        Q(schedule_days="ALL") | Q(schedule_days__contains=tomorrow_day_of_week)
    )

    if request.method == 'POST':
        # Truyền queryset vào form
        form = BetForm(
            request.POST,
            stations_today=stations_today_open,
            stations_tomorrow=stations_tomorrow
        )

        if form.is_valid():
            data = form.cleaned_data

            station_id = data['station']
            try:
                selected_station = LotteryStation.objects.get(id=station_id)
            except LotteryStation.DoesNotExist:
                messages.error(request, "Đài bạn chọn không hợp lệ.")
                return redirect('place_bet')

            number_list = data['number']
            amount_per_bet = data['amount']
            bet_type = data['bet_type']

            # --- XÁC ĐỊNH NGÀY CƯỢC (Quan trọng) ---
            if selected_station in stations_today_open:
                bet_date = today_date
            elif selected_station in stations_tomorrow:
                bet_date = tomorrow_date
            else:
                messages.error(request, f"Đài {selected_station.name} đã qua giờ chốt cược hoặc không quay hôm nay.")
                return redirect('place_bet')

            user_wallet = request.user.wallet
            total_amount_needed = amount_per_bet * len(number_list)

            if user_wallet.balance < total_amount_needed:
                messages.error(request, f"Số dư không đủ. Cần {total_amount_needed:,.0f}đ.")
                return redirect('place_bet')

            new_bet_messages = []
            updated_bets_messages = []

            try:
                # Dùng db_transaction (đã sửa)
                with db_transaction.atomic():
                    user_wallet.balance -= total_amount_needed
                    user_wallet.save()

                    for number in number_list:
                        Transaction.objects.create(  # Model
                            wallet=user_wallet,
                            amount=amount_per_bet,
                            transaction_type='BET',
                            description=f"Cược {bet_type} {selected_station.name} số {number} ngày {bet_date}"
                        )

                        existing_bet = Bet.objects.filter(
                            user=request.user, station=selected_station,
                            bet_type=bet_type, number=number,
                            date=bet_date, status='PENDING'
                        ).first()

                        formatted_amount = f"{amount_per_bet:,.0f}đ"

                        if existing_bet:
                            existing_bet.amount += amount_per_bet
                            existing_bet.save()
                            formatted_total_bet = f"{existing_bet.amount:,.0f}đ"
                            msg = f"Ghi thêm {bet_type} {selected_station.name} {number} (ngày {bet_date}) là: {formatted_total_bet}"
                            updated_bets_messages.append(msg)

                        else:
                            Bet.objects.create(
                                user=request.user, station=selected_station,
                                bet_type=bet_type, number=number,
                                amount=amount_per_bet, date=bet_date,
                                status='PENDING'
                            )
                            msg = f"Cược mới {bet_type} {selected_station.name} số: {number} (ngày {bet_date}) là: {formatted_amount}"
                            new_bet_messages.append(msg)

                # Gửi tin nhắn
                for msg in new_bet_messages: messages.success(request, msg)
                for msg in updated_bets_messages: messages.success(request, msg)
                formatted_total = f"{total_amount_needed:,.0f}đ"
                messages.info(request, f"Tổng tiền vừa cược {selected_station.name}: {formatted_total}")
                return redirect('place_bet')

            except IntegrityError:
                messages.error(request,
                               f"Lỗi: Một trong các số cược (ngày {bet_date}, đài {selected_station.name}) đã được xử lý.")
            except Exception as e:
                messages.error(request, f"Có lỗi xảy ra: {e}")

    else:
        # Khi GET, truyền 2 queryset vào form
        form = BetForm(
            stations_today=stations_today_open,
            stations_tomorrow=stations_tomorrow
        )

    today_bets = Bet.objects.filter(user=request.user, date=today_date)
    tomorrow_bets = Bet.objects.filter(user=request.user, date=tomorrow_date)

    return render(request, 'lottery/place_bet.html', {
        'form': form,
        'today_bets': today_bets,
        'tomorrow_bets': tomorrow_bets,
        'tomorrow_date_for_display': tomorrow_date,
        'today_date_for_display': today_date,
    })


# --- VIEW XÓA CƯỢC (Đã sửa lỗi import) ---
@login_required
def delete_bet_view(request, bet_id):
    bet = get_object_or_404(Bet, id=bet_id, user=request.user)

    if bet.status != 'PENDING':
        messages.error(request, "Không thể xóa cược đã xử lý.")
        return redirect('place_bet')

    cutoff_hour = bet.station.cutoff_hour
    local_now = get_local_now()

    if bet.date == local_now.date():
        if local_now.hour >= cutoff_hour:
            messages.error(request, f"Đã qua giờ chốt cược ({cutoff_hour}h00) của đài {bet.station.name}.")
            return redirect('place_bet')

    try:
        with db_transaction.atomic():  # Sửa lỗi
            wallet = request.user.wallet
            wallet.balance += bet.amount
            wallet.save()

            Transaction.objects.create(  # Sửa lỗi
                wallet=wallet,
                amount=bet.amount,
                transaction_type='REFUND',
                description=f"Hoàn tiền (hủy cược {bet.station.name} {bet.bet_type} {bet.number})"
            )
            bet_info = f"{bet.station.name} {bet.bet_type} {bet.number}"
            bet_amount = bet.amount
            bet.delete()
        messages.success(request, f"Đã xóa cược {bet_info} và hoàn {bet_amount:,.0f}đ vào ví.")
    except Exception as e:
        messages.error(request, f"Lỗi khi xóa cược: {e}")

    return redirect('place_bet')


# --- VIEW UPLOAD ADMIN (Đã sửa lỗi import) ---
@user_passes_test(is_admin)
def admin_upload_result_view(request):
    form = ImageUploadForm()

    if request.method == 'POST':
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            image_file = request.FILES['image']
            result_date = form.cleaned_data['date']
            selected_station = form.cleaned_data['station']

            if LotteryResult.objects.filter(date=result_date, station=selected_station).exists():
                messages.error(request, f"Kết quả cho {selected_station.name} ngày {result_date} đã tồn tại.")
                return redirect('admin_upload_result')

            try:
                prizes_list = get_results_from_gemini(
                    image_file,
                    selected_station.prize_count
                )
                new_result = LotteryResult.objects.create(
                    date=result_date,
                    station=selected_station,
                    prizes=prizes_list
                )
                messages.success(request,
                                 f"Đã lưu kết quả {selected_station.name} ngày {result_date}! GĐB: {new_result.de_number}")

                messages.info(request, "Bắt đầu tính toán thắng/thua...")
                success_msg, error_msg = process_lottery_results(result_date, selected_station.id)

                if error_msg: messages.error(request, error_msg)
                if success_msg: messages.success(request, success_msg)
                return redirect('admin_upload_result')

            except Exception as e:
                messages.error(request, f"LỖI NGHIÊM TRỌNG: {e}")

    return render(request, 'lottery/admin_upload_result.html', {'form': form})