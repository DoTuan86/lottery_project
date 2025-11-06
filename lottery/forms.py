from django import forms
from .models import Bet


class BetForm(forms.Form):
    bet_type = forms.ChoiceField(
        choices=Bet.BET_TYPES,
        label="Loại cược"
    )

    # === SỬA TRƯỜNG NÀY ===
    # Bỏ max_length=2, min_length=2
    number = forms.CharField(
        label="Các số cược (mỗi số 2 chữ số)",
        widget=forms.TextInput(attrs={'placeholder': 'Ví dụ: 15253534 hoặc 15 25 35 34'})
    )
    # === KẾT THÚC SỬA ===

    amount = forms.DecimalField(
        label="Số tiền cược (cho mỗi số)",
        min_value=1000,
        widget=forms.NumberInput(attrs={'placeholder': 'Tối thiểu 1,000'})
    )

    # === THÊM HÀM NÀY ===
    def clean_number(self):
        """
        Hàm này sẽ bóc tách chuỗi số cược.
        Ví dụ: "15 25 35" hoặc "152535" -> trả về ['15', '25', '35']
        """
        raw_numbers = self.cleaned_data['number']

        # 1. Chuẩn hóa chuỗi: xóa hết dấu cách, dấu phẩy, v.v.
        normalized_string = raw_numbers.replace(" ", "").replace(",", "").replace("\n", "").replace(".", "")

        if not normalized_string:
            raise forms.ValidationError("Bạn chưa nhập số cược.")

        # 2. Kiểm tra xem chuỗi có toàn số không
        if not normalized_string.isdigit():
            raise forms.ValidationError("Chỉ được nhập số.")

        # 3. Kiểm tra xem độ dài có phải là số chẵn không (vì mỗi số 2 chữ số)
        if len(normalized_string) % 2 != 0:
            raise forms.ValidationError("Chuỗi số phải có độ dài chẵn (ví dụ: 152535).")

        # 4. Bóc tách chuỗi thành danh sách các số (mỗi số 2 chữ số)
        number_list = [normalized_string[i:i + 2] for i in range(0, len(normalized_string), 2)]

        # 5. Loại bỏ trùng lặp (nếu người dùng nhập 151525 -> chỉ cược 15, 25)
        unique_numbers = list(set(number_list))

        return unique_numbers