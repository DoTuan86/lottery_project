from django import forms
from .models import Bet

class BetForm(forms.Form):
    bet_type = forms.ChoiceField(
        choices=Bet.BET_TYPES,
        label="Loại cược"
    )
    number = forms.CharField(
        label="Số cược",
        max_length=2,
        min_length=2,
        widget=forms.TextInput(attrs={'placeholder': 'Ví dụ: 86'})
    )
    amount = forms.DecimalField(
        label="Số tiền cược",
        min_value=1000, # Ví dụ: cược tối thiểu 1.000đ
        widget=forms.NumberInput(attrs={'placeholder': 'Tối thiểu 1,000', 'step': '1000'})
    )

    def clean_number(self):
        """Đảm bảo số cược là 2 chữ số"""
        number = self.cleaned_data['number']
        if not number.isdigit() or len(number) != 2:
            raise forms.ValidationError("Số cược phải là 2 chữ số.")
        return number