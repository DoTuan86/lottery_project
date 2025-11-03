from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError
from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('username', 'phone_number')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Tên người dùng'
        self.fields['phone_number'].label = 'Số điện thoại'
        self.fields['password1'].label = 'Mật Khẩu'
        self.fields['password2'].label = 'Nhập lại mật khẩu'

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Mật khẩu nhập lại không khớp.')

        try:
            password_validation.validate_password(password1, self.instance)
        except ValidationError as e:
            code_map = {
                'password_too_similar': 'Mật khẩu không được quá giống thông tin cá nhân của bạn.',
                'password_too_short': 'Mật khẩu phải chứa ít nhất 8 ký tự.',
                'password_too_common': 'Mật khẩu quá phổ biến.',
                'password_entirely_numeric': 'Mật khẩu không được chỉ chứa chữ số.',
            }
            messages = []
            for err in e.error_list:
                messages.append(code_map.get(err.code, str(err)))
            raise forms.ValidationError(messages)

        return password2